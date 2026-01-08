"""
Similarity search feature implementation.

This feature finds similarities with historical amendments.
"""

import asyncio
import logging
import logging.config
from typing import Any

import pandas as pd

from graal.api.services.similarity_db_manifest_service import (
    get_similarity_db_manifest_service,
)
from graal.core.feature_interface import BaseFeature, FeatureInput, FeatureOutput
from graal.core.text_normalizers import TextNormalizerFactory
from graal.similarities.similarity_search_handler import (
    SimilaritySearchHandler,
)
from graal.utils.amendment_pre_processor import AmendmentPreProcessor
from graal.utils.similarity_db_loader import get_similarity_db_loader

logging.config.fileConfig("logging.conf")


class SimilaritySearchFeature(BaseFeature):
    """
    Finds similarities with historical amendments.
    """

    def __init__(self, config: dict[str, Any]):
        super().__init__("similarity_search")
        self.normalizer = TextNormalizerFactory.get_normalizer("similarity_search")
        self.config = config

        if not config:
            raise ValueError("SimilaritySearchFeature requires config parameter")

    def get_required_columns(self) -> set[str]:
        """Similarity search requires these columns."""
        return {"Corps amdt", "Exposé amdt", "amdt_idx", "Num article"}

    def get_output_columns(self) -> set[str]:
        """Similarity search can update these columns based on configuration."""
        similarity_config = self.config.get("similarity_search", {})
        columns_to_copy_config = similarity_config.get("columns_to_copy", {})

        if not columns_to_copy_config:
            raise ValueError(
                "Columns to copy configuration must be specified in similarity_search.columns_to_copy"
            )

        # Get enabled columns from config
        enabled_columns = set()
        for column, config_dict in columns_to_copy_config.items():
            if config_dict.get("enabled", False):
                enabled_columns.add(column)

        # Always include "Commentaires" regardless of config
        enabled_columns.add("Commentaires")

        return enabled_columns

    def is_enabled(self, config: dict[str, Any]) -> bool:
        """Check if similarity search is enabled."""
        similarity_config = config.get("similarity_search", {})
        return similarity_config.get("enabled", False)

    def get_columns_to_clear(self, config: dict[str, Any]) -> set[str]:
        """Return columns to clear if similarity search is enabled."""
        if not self.is_enabled(config):
            return set()

        # Reuse logic from get_output_columns but exclude non-clearable columns
        output_columns = self.get_output_columns()
        # Remove 'Commentaires' as it's appended to, not cleared
        clearable_columns = output_columns - {"Commentaires"}
        return clearable_columns

    def process(self, feature_input: FeatureInput) -> FeatureOutput:
        """
        Process amendments for similarity search.

        This creates its own normalized text internally without affecting the input data.
        """
        # Work with our own copy
        working_df = feature_input.amendments_df.copy()
        similarity_config = feature_input.config.get("similarity_search", {})

        # Get processing options from config
        should_overwrite = similarity_config.get("should_overwrite", True)

        # Get columns to copy configuration
        columns_to_copy_config = similarity_config.get("columns_to_copy", {})
        if not columns_to_copy_config:
            raise ValueError(
                "Columns to copy configuration must be specified in similarity_search.columns_to_copy"
            )

        # Load historical amendments from S3 Parquet
        old_amendments_df = self._load_similarity_database(similarity_config)

        # Create our own normalized version for processing
        normalized_working_df = self._create_normalized_dataframe(working_df)

        # Get similarity thresholds
        clustering_similarity_thresholds = similarity_config.get(
            "clustering_similarity_thresholds", {"Exposé amdt": 0.4, "Corps amdt": 0.4}
        )
        fuzzy_match_similarity_thresholds = similarity_config.get(
            "fuzzy_match_similarity_thresholds", {"Exposé amdt": 0.4, "Corps amdt": 0.9}
        )
        similarity_threshold_overrides = similarity_config.get(
            "similarity_threshold_overrides",
            {"Exposé amdt": {"amendement redactionnel": 0.95}},
        )

        # Process similarity search
        result_df = SimilaritySearchHandler.populate(
            preprocessed_old_amendments_df=old_amendments_df,
            preprocessed_new_amendments_df=normalized_working_df,
            original_new_amendments_df=working_df,
            clustering_similarity_thresholds=clustering_similarity_thresholds,
            fuzzy_match_similarity_thresholds=fuzzy_match_similarity_thresholds,
            similarity_threshold_overrides=similarity_threshold_overrides,
            column_filtering_funcs={
                "Corps amdt": SimilaritySearchHandler.filter_old_amendments_by_project,
            },
            column_group_by_columns={
                "Corps amdt": ["Num article"],
            },
            columns_to_copy_config=columns_to_copy_config,
            should_overwrite=should_overwrite,
        )
        result_df.set_index("amdt_idx", inplace=True)

        output_columns = self.get_output_columns()

        # Create final result with declared output columns
        final_df = feature_input.amendments_df.copy()

        # Only include output columns if we have actual results to report
        # Don't create empty columns that would interfere with concatenation from other features
        if len(result_df) > 0:
            for col in output_columns:
                if col in result_df.columns:
                    # Initialize column with pd.NA for all rows
                    if col not in final_df.columns:
                        final_df[col] = pd.NA
                    # Then update only the rows with search results
                    final_df.loc[result_df.index, col] = result_df[col]

        return FeatureOutput(
            amendments_df=final_df,
            outputs={
                "processed_amendments": len(result_df),
                "enabled_columns": list(output_columns),
            },
        )

    def _create_normalized_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Create a normalized version of the dataframe for internal processing.

        This applies all the necessary preprocessing that similarity search needs
        without affecting the original data.
        """
        normalized_df = df.copy()

        # Drop empty rows
        normalized_df = AmendmentPreProcessor.drop_empty_rows_in_columns(
            amendments_df=normalized_df, columns_to_filter=["Exposé amdt", "Corps amdt"]
        )

        # Normalize the text columns using our feature-specific normalizer
        for column in ["Exposé amdt", "Corps amdt"]:
            normalized_df[column] = normalized_df[column].apply(
                lambda x: self.normalizer.normalize_for_feature(str(x))
            )

        # Handle common amendment bodies
        normalized_df = AmendmentPreProcessor.handle_common_amendment_bodies(
            amendments_df=normalized_df
        )

        return normalized_df

    def _load_similarity_database(
        self, similarity_config: dict[str, Any]
    ) -> pd.DataFrame:
        """Load similarity database from S3 Parquet.

        Args:
            similarity_config: The similarity search configuration

        Returns:
            pd.DataFrame: The loaded similarity database

        Raises:
            ValueError: If database_id is not configured
            FileNotFoundError: If the specified file is not found in S3
        """
        database_id = similarity_config.get("database_id")

        if not database_id:
            raise ValueError(
                "No similarity database configured. Please provide 'database_id' "
                "with the UUID of the database manifest."
            )

        # Resolve S3 path from manifest using database_id
        manifest_service = get_similarity_db_manifest_service()
        s3_path = asyncio.run(manifest_service.resolve_s3_path_for_db(database_id))
        logging.info(
            f"Loading similarity database from S3 (id={database_id}): {s3_path}"
        )

        loader = get_similarity_db_loader()
        df = asyncio.run(loader.load_from_s3(s3_path))
        logging.info(f"Loaded Parquet database for DB {database_id}, shape: {df.shape}")
        return df
