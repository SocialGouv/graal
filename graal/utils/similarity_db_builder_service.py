"""
Service for building similarity databases from amendments.

This service processes amendments from various sources (JSON, Excel) and
applies preprocessing and deduplication. Following the Single Responsibility
Principle, it ONLY builds the similarity database DataFrame and does NOT
handle file I/O operations (local saving, S3 uploads). File persistence
is the responsibility of the caller.
"""

import logging
from pathlib import Path
from typing import Optional

import pandas as pd

from graal.allotment.allotment_handler import AllotmentHandler
from graal.custom_types import Acronym, IntIndex
from graal.similarities.similarity_search_handler import SimilaritySearchHandler
from graal.utils.amendment_file_handlers import AmendmentFileHandlerRegistry
from graal.utils.amendment_pre_processor import AmendmentPreProcessor
from graal.utils.config.base_config import InputFileConfig
from graal.utils.sheet_data_loader import SheetDataLoader

logger = logging.getLogger(__name__)


# Custom exception classes
class SimilarityDBBuildError(Exception):
    """Base exception for similarity database building errors."""

    pass


class InvalidProjectError(SimilarityDBBuildError):
    """Raised when project configuration is invalid."""

    pass


class EmptyDatasetError(SimilarityDBBuildError):
    """Raised when no amendments are available after preprocessing."""

    pass


class SimilarityDatabaseBuilderService:
    """
    Service for building similarity databases from amendments.

    This service is responsible
    for building the similarity database DataFrame. It processes amendments from
    various sources (JSON, Excel), applies preprocessing and deduplication, and
    returns the processed DataFrame.
    """

    def __init__(
        self,
        office_config_file_path: str = "Fichier de configuration GRAAL - DSS - latest.xlsx",
    ):
        """
        Initialize the similarity database builder service.

        Args:
            office_config_file_path: Path to the office configuration Excel file
                                    containing acronym mappings (default: DSS config file).
        """
        self._office_config_file_path = office_config_file_path
        logger.info(
            f"Initialized SimilarityDatabaseBuilderService with office config: {office_config_file_path}"
        )

    async def build_database(
        self,
        amendment_files: dict[Path, InputFileConfig],
        drop_empty_columns: Optional[list[str]] = None,
        similarity_threshold: float = 0.99,
        eps: float = 0.4,
        group_by_columns: Optional[list[str]] = None,
        office_config_file_path: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Build a similarity database from project amendments.

        This method orchestrates the entire database building process:
        - Load and preprocess amendments from JSON and Excel
        - Apply deduplication via clustering
        - Return the processed DataFrame

        Args:
            amendment_files: Files to load in the DB (path -> config dict).
            drop_empty_columns: Columns where empty rows should be dropped.
            similarity_threshold: Threshold for Levenshtein refinement in clustering (default: 0.99).
            eps: Epsilon value for DBSCAN clustering (default: 0.4).
            group_by_columns: Columns to group by during clustering.
            office_config_file_path: Path to the office configuration Excel file.
                                    If provided, overrides the instance default.

        Returns:
            pd.DataFrame: The processed similarity database.

        Raises:
            ValueError: If output_format is not 'parquet'.
            InvalidProjectError: If no valid projects are found.
            EmptyDatasetError: If no amendments are available after preprocessing.
            SimilarityDBBuildError: If an unexpected error occurs during building.
        """

        if drop_empty_columns is None:
            drop_empty_columns = ["Réponse"]

        if group_by_columns is None:
            group_by_columns = ["Lecture", "origin_project", "Num article"]

        try:
            logger.info("=" * 80)
            logger.info("Starting similarity database build process")
            logger.info(f"Similarity threshold: {similarity_threshold}, eps: {eps}")
            logger.info("=" * 80)

            # Load project configurations
            logger.info("Loading project configurations...")

            # Determine which config file to use
            config_file_to_use = (
                office_config_file_path
                if office_config_file_path is not None
                else self._office_config_file_path
            )

            # Load acronym mappings from office config
            logger.info(f"Loading acronym mappings from: {config_file_to_use}")
            sheet_loader = SheetDataLoader(config_file_to_use)
            office_config_file = sheet_loader.excel_data
            acronym_mapping = AmendmentPreProcessor.load_acronyms(
                office_config_file["Acronymes"]
            )
            logger.info(f"Loaded {len(acronym_mapping)} acronym mappings")

            # Load and preprocess amendments
            logger.info("Loading and preprocessing amendments...")
            amendments_df = self._load_and_preprocess_amendments(
                amendment_files=amendment_files,
                acronym_mapping=acronym_mapping,
                empty_columns_to_drop=drop_empty_columns,
            )

            if amendments_df.empty:
                raise EmptyDatasetError(
                    "No amendments available after preprocessing. Check input files and filters."
                )

            logger.info(
                f"Preprocessed {len(amendments_df)} amendments, starting deduplication..."
            )

            # Apply clustering and deduplication
            logger.info("Applying deduplication via clustering...")
            filtered_df, _clusters = AllotmentHandler.process_allotments(
                amendments_df=amendments_df,
                allotment_column="Exposé amdt",
                similarity_threshold=similarity_threshold,
                group_by_columns=group_by_columns,
                eps=eps,
                removal_strategy_func=self._get_all_indices_oldest_or_shorter_responses,
            )

            logger.info(
                f"Deduplication complete: {len(amendments_df)} -> {len(filtered_df)} amendments "
                f"({len(amendments_df) - len(filtered_df)} duplicates removed)"
            )

            logger.info("=" * 80)
            logger.info(
                f"Successfully built similarity database with {len(filtered_df)} unique amendments"
            )
            logger.info("=" * 80)

            return filtered_df

        except InvalidProjectError:
            raise
        except EmptyDatasetError:
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error building similarity database: {e}", exc_info=True
            )
            raise SimilarityDBBuildError(
                f"Failed to build similarity database: {e}"
            ) from e

    def _load_and_preprocess_amendments(
        self,
        amendment_files: dict[Path, InputFileConfig],
        acronym_mapping: dict[Acronym, str],
        empty_columns_to_drop: list[str],
    ) -> pd.DataFrame:
        """
        Load and preprocess amendments from JSON and Excel files.

        Orchestrates loading from both JSON and Excel sources, applies
        similarity preprocessing, and performs necessary cleanup.

        Args:
            amendment_files: Files to load in the DB (path -> config dict).
            acronym_mapping: Mapping of acronyms to full text.
            drop_empty_columns: Columns to drop if empty.

        Returns:
            pd.DataFrame: Preprocessed amendments ready for clustering.

        Raises:
            Exception: If loading or preprocessing fails.
        """
        try:
            # Initialize handler registry
            handler_registry = AmendmentFileHandlerRegistry()

            # Group files by handler type
            grouped_files = handler_registry.group_files_by_handler(amendment_files)

            # Load and preprocess amendments from each file type
            dataframes: list[pd.DataFrame] = []

            for handler, file_configs in grouped_files.items():
                handler_name = handler.__class__.__name__
                file_count = len(file_configs)
                logger.info(f"Loading {file_count} files using {handler_name}...")

                # Load amendments using the handler
                df = handler.load_amendments(file_configs)

                # Apply similarity preprocessing
                df = SimilaritySearchHandler.preprocess_for_similarity(
                    df, acronym_mapping
                )

                logger.info(f"Loaded {len(df)} amendments using {handler_name}")
                dataframes.append(df)

            # Combine all DataFrames
            if not dataframes:
                amendments_df = pd.DataFrame()
                logger.info("No files to load")
            elif len(dataframes) == 1:
                amendments_df = dataframes[0]
            else:
                # Concatenate multiple dataframes sequentially
                amendments_df = dataframes[0]
                for df in dataframes[1:]:
                    amendments_df = AmendmentPreProcessor.concatenate_dataframes(
                        amendments_df, df
                    )
                logger.info(f"Combined amendments from {len(dataframes)} file types")

            if amendments_df.empty:
                logger.warning("No amendments loaded from any source")
                return amendments_df

            logger.info(f"Total amendments loaded: {len(amendments_df)}")

            # Drop empty rows in specified columns
            amendments_df = AmendmentPreProcessor.drop_empty_rows_in_columns(
                amendments_df, empty_columns_to_drop
            )
            logger.info(f"After dropping empty rows: {len(amendments_df)} amendments")

            # Apply universal preprocessing (remove gage sentences with unidecode)
            logger.info(
                "Applying universal preprocessing to Corps amdt and Exposé amdt..."
            )
            amendments_df = AmendmentPreProcessor.apply_universal_preprocessing(
                amendments_df=amendments_df,
                acronym_mapping=None,  # No acronym replacement for similarity DB
                columns_to_process=["Corps amdt", "Exposé amdt"],
            )

            # Handle empty Corps amdt by generating placeholder text
            logger.info("Handling empty Corps amdt entries...")
            for index, row in amendments_df.iterrows():
                if pd.isna(row["Corps amdt"]) or row["Corps amdt"] in [None, ""]:
                    amendments_df.at[index, "Corps amdt"] = (
                        f"Ce corps d'amendement peut être ignoré, il a été ajouté pour "
                        f"faciliter le traitement des amendements {index}"
                    )

            logger.info("Preprocessing complete")
            return amendments_df

        except Exception as e:
            logger.error(
                f"Error loading and preprocessing amendments: {e}", exc_info=True
            )
            raise

    @staticmethod
    def _get_all_indices_oldest_or_shorter_responses(
        df: pd.DataFrame, cluster: list[IntIndex]
    ) -> list[IntIndex]:
        """
        Strategy function for removing duplicates from a cluster.

        Keeps the most recent amendment with the longest response,
        returns indices of every other amendment for removal.

        Args:
            df: DataFrame containing all amendments.
            cluster: List of amendment indices in the cluster.

        Returns:
            List of amendment indices to remove from the cluster.
        """
        filtered_df = df[df["amdt_idx"].isin(cluster)].sort_values(
            by=["timestamp", "Réponse"],
            ascending=[False, False],
            key=lambda x: x if x.name != "Réponse" else x.str.len(),
        )
        # Return all but the first (keep most recent with longest response)
        return filtered_df["amdt_idx"].tolist()[1:]


# Global instance
_similarity_db_builder: SimilarityDatabaseBuilderService | None = None


def get_similarity_db_builder() -> SimilarityDatabaseBuilderService:
    """
    Get the global SimilarityDatabaseBuilderService instance.

    Returns:
        SimilarityDatabaseBuilderService: The global builder instance.
    """
    global _similarity_db_builder
    if _similarity_db_builder is None:
        _similarity_db_builder = SimilarityDatabaseBuilderService()
    return _similarity_db_builder
