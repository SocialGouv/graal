"""
Pipeline implementation for GRAAL.

This pipeline separates preprocessing steps (like allotment) from
independent features to eliminate cross-dependencies and side effects.
"""

import logging
import logging.config
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from graal.core.feature_interface import (
    BaseFeature,
)
from graal.core.pipeline_orchestrator import PipelineOrchestrator
from graal.features.allotment_feature import AllotmentFeature
from graal.features.attribution_feature import (
    AttributionFeature,
)
from graal.features.opinion_feature import OpinionFeature
from graal.features.similarities_within_lecture_feature import (
    SimilaritiesWithinLecturesFeature,
)
from graal.features.similarity_search_feature import SimilaritySearchFeature
from graal.features.summary_feature import (
    SummaryGenerationFeature,
)
from graal.summary.llm_factory import create_llm_api_clients, get_rate_limiting_config
from graal.summary.summary_generation_load_balancer import SummaryGenerationLoadBalancer
from graal.utils.amendment_pre_processor import AmendmentPreProcessor
from graal.utils.config.config_preprocessor import ConfigPreprocessor
from graal.utils.text_utils import remove_gage_sentences

logging.config.fileConfig("logging.conf")


class ProcessingPipeline:
    """
    Independent pipeline that processes amendments with separated concerns.

    Architecture:
    1. Initial preprocessing (load, clean, basic normalization)
    2. Preprocessing features (allotment filtering) - run first
    3. Regular features (attribution, summary, similarity, etc.)
    4. Result merging and output
    """

    def __init__(self):
        # Features are created in run() method with their dependencies
        pass

    def run(self, config: dict[str, Any]) -> None:
        """
        Run the processing pipeline.

        Args:
            config: Full configuration dictionary from YAML
        """
        logging.info("Starting pipeline processing")
        start_time = time.time()

        # Phase 0: Preprocess configuration (resolve environment variables, validate paths)
        config_preprocessor = ConfigPreprocessor(
            validate_paths=False
        )  # Don't validate paths that might not exist yet
        preprocessed_config = config_preprocessor.preprocess_config(config)

        # Phase 1: Load and prepare data
        amendments_df, dependencies = self._load_and_prepare_data(preprocessed_config)

        # Store preprocessed original dataframe for allotment population (before clearing)
        dependencies["preprocessed_original_df"] = amendments_df.copy()

        # Phase 2: Get features from dependencies (already created during data preparation)
        preprocessing_features = dependencies["preprocessing_features"]
        features = dependencies["features"]

        # Store original dataframe AFTER clearing columns - this ensures that
        # _preserve_original_values() will preserve the cleared (None) values
        # instead of the old data that was supposed to be erased
        dependencies["original_df"] = amendments_df.copy()

        # Phase 3: Run orchestrated processing
        orchestrator = PipelineOrchestrator(
            preprocessing_features=preprocessing_features,
            features=features,
            concatenated_columns={
                "Commentaires"
            },  # Configure columns that should be concatenated
        )
        result_df, processing_outputs = orchestrator.process(
            amendments_df=amendments_df,
            config=preprocessed_config,
        )

        # Phase 4: Handle special post-processing and output
        self._finalize_and_output(
            result_df, preprocessed_config, dependencies, processing_outputs
        )

        end_time = time.time()
        logging.info(
            f"Independent pipeline completed in {end_time - start_time:.2f} seconds"
        )

    def _load_and_prepare_data(
        self, config: dict[str, Any]
    ) -> tuple[pd.DataFrame, dict[str, Any]]:
        """
        Load and prepare data for processing and create dependency objects.

        This handles the initial data loading and basic cleaning that
        all features need, without feature-specific normalization.
        """
        DATA_FOLDER = os.environ["DATA_FOLDER"]

        # Load configuration Excel file (path is already preprocessed)
        graal_config_file = Path(config["paths"]["graal_config_file"])
        config_excel = pd.read_excel(graal_config_file, sheet_name=None)

        # Build input files configuration
        input_files_config = self._build_input_files_config(config)

        # Load amendments from input files
        amendments_df = self._load_amendments(input_files_config)

        # Apply mission filter if specified
        if config.get("mission_short_title_filter"):
            amendments_df = self._apply_mission_filter(
                amendments_df, config["mission_short_title_filter"]
            )

        # Handle placeholder amendment bodies if enabled
        if config.get("processing_options", {}).get("placeholder_amdt_body", False):
            amendments_df = self._add_placeholder_bodies(amendments_df)

        # Load and apply basic preprocessing (not feature-specific)
        acronym_mapping = AmendmentPreProcessor.load_acronyms(config_excel["Acronymes"])

        # Drop empty rows and replace acronyms
        amendments_df = AmendmentPreProcessor.drop_empty_rows_in_columns(
            amendments_df=amendments_df,
            columns_to_filter=["Exposé amdt"],
        )
        amendments_df = AmendmentPreProcessor.replace_acronyms(
            amendments_df=amendments_df,
            acronym_mapping=acronym_mapping,
            columns_to_normalize=["Exposé amdt", "Corps amdt"],
        )

        # Remove gage sentences (this is universal preprocessing)
        amendments_df["Corps amdt"] = amendments_df["Corps amdt"].apply(
            lambda text: remove_gage_sentences(text)
        )
        amendments_df["Exposé amdt"] = amendments_df["Exposé amdt"].apply(
            lambda text: remove_gage_sentences(text)
        )

        # Handle common amendment patterns
        amendments_df = (
            AmendmentPreProcessor.handle_common_amendment_expose_and_redactional(
                amendments_df=amendments_df, add_redactional_column=True
            )
        )

        # Create LLM clients for summary generation
        llm_api_clients = create_llm_api_clients(config)
        rate_limiting_config = get_rate_limiting_config(config)
        summary_gen_load_balancer = SummaryGenerationLoadBalancer(
            clients=llm_api_clients,
            queue_timeout=4,
            max_retries=5,
            rate_limiting_config=rate_limiting_config,
        )

        # Create all features to determine columns to clear
        preprocessing_features = [
            AllotmentFeature(config_excel=config_excel),
        ]

        features = [
            AttributionFeature(config_excel=config_excel),
            SimilaritySearchFeature(config=config),
            SummaryGenerationFeature(
                summary_gen_load_balancer=summary_gen_load_balancer,
                acronym_mapping=acronym_mapping,
                config_excel=config_excel,
            ),
            OpinionFeature(config_excel=config_excel),
            SimilaritiesWithinLecturesFeature(),
        ]

        all_features = preprocessing_features + features

        # Clear columns that will be overridden by features
        columns_to_clear = self._determine_columns_to_clear(config, all_features)
        amendments_df = AmendmentPreProcessor.clear_columns_to_be_overridden(
            amendments_df=amendments_df, columns_to_clear=columns_to_clear
        )

        # Prepare dependencies for features
        dependencies = {
            "config_excel": config_excel,
            "acronym_mapping": acronym_mapping,
            "summary_gen_load_balancer": summary_gen_load_balancer,
            "data_folder": DATA_FOLDER,
            "graal_config_file": str(graal_config_file),
            "preprocessing_features": preprocessing_features,
            "features": features,
        }

        return amendments_df, dependencies

    def _build_input_files_config(
        self, config: dict[str, Any]
    ) -> dict[Path, dict[str, Any]]:
        """Build input files configuration."""
        input_files_config = {}

        for input_file_config in config["input_files"]:
            # Path is already preprocessed
            file_path = Path(input_file_config["path"])

            # Convert timestamp dict to datetime and then to timestamp
            timestamp_dict = input_file_config["default_processing_timestamp"]
            timestamp = int(
                datetime(
                    year=timestamp_dict["year"],
                    month=timestamp_dict["month"],
                    day=timestamp_dict["day"],
                ).timestamp()
            )

            input_files_config[file_path] = {
                "default_processing_timestamp": timestamp,
                "origin_project": input_file_config["origin_project"],
            }

        return input_files_config

    def _load_amendments(
        self, input_files_config: dict[Path, dict[str, Any]]
    ) -> pd.DataFrame:
        """Load amendments from input files."""
        file_path = next(iter(input_files_config.keys()))
        suffix = file_path.suffix.lower()

        if suffix in [".xlsx", ".xls"]:
            amendments_df = AmendmentPreProcessor.load_amendments_excel(
                [file_path], input_files_config
            )
        elif suffix == ".json":
            amendments_df = AmendmentPreProcessor.load_amendments_json(
                [file_path], input_files_config
            )
        else:
            raise ValueError(f"Unsupported file type: {suffix}")

        return amendments_df

    def _apply_mission_filter(
        self, amendments_df: pd.DataFrame, mission_filters: list[str]
    ) -> pd.DataFrame:
        """Apply mission short title filter."""
        if not mission_filters:
            return amendments_df

        amendments_df["Mission"] = (
            amendments_df["Mission"]
            .str.normalize("NFKD")
            .str.encode("ascii", errors="ignore")
            .str.decode("utf-8")
            .str.lower()
        )
        # Transform NaN values in "Mission" into empty strings
        amendments_df["Mission"] = amendments_df["Mission"].fillna("")
        amendments_df = amendments_df[
            amendments_df["Mission"].apply(
                lambda x: any(x.startswith(prefix) for prefix in mission_filters)
            )
        ]
        return amendments_df

    def _add_placeholder_bodies(self, amendments_df: pd.DataFrame) -> pd.DataFrame:
        """Add placeholder bodies for empty amendments."""
        for index, row in amendments_df.iterrows():
            amendments_df.at[index, "Corps amdt"] = (
                row["Corps amdt"]
                if pd.notna(row["Corps amdt"]) and row["Corps amdt"] not in [None, ""]
                else f"Ce corps d'amendement peut être ignoré, il a été ajouté pour faciliter le traitement des amendements {index}"
            )
        return amendments_df

    def _determine_columns_to_clear(
        self, config: dict[str, Any], all_features: list[BaseFeature]
    ) -> set[str]:
        """Determine which columns should be cleared based on enabled features."""
        columns_to_clear = {"Commentaires"}  # Always clear comments

        # Get columns to clear from all features
        for feature in all_features:
            feature_columns = feature.get_columns_to_clear(config)
            columns_to_clear.update(feature_columns)

        return columns_to_clear

    def _finalize_and_output(
        self,
        result_df: pd.DataFrame,
        config: dict[str, Any],
        dependencies: dict[str, Any],
        processing_outputs: dict[str, Any],
    ) -> None:
        """
        Handle final processing and output generation.
        """
        # Handle no_value_overwrite option
        if config.get("processing_options", {}).get("no_value_overwrite", False):
            original_df = dependencies.get("original_df")
            if original_df is not None:
                result_df = self._preserve_original_values(
                    result_df, original_df, config
                )

        # Handle allotment result population (special case since allotment affects structure)
        allotment_outputs = processing_outputs.get("allotment", {})
        if allotment_outputs and "allotted_clusters" in allotment_outputs:
            result_df = self._populate_allotment_results(
                result_df,
                dependencies.get("preprocessed_original_df"),
                allotment_outputs["allotted_clusters"],
            )

        # Generate output files
        self._save_results(result_df, config)

        # Log processing summary
        self._log_processing_summary(processing_outputs)

    def _preserve_original_values(
        self, result_df: pd.DataFrame, original_df: pd.DataFrame, config: dict[str, Any]
    ) -> pd.DataFrame:
        """Preserve original values for specified columns."""
        # Determine which columns should preserve original values
        columns_to_preserve = set()

        if config.get("summary_generation", {}).get("enabled", False):
            columns_to_preserve.add("Objet amdt")

        if config.get("attribution", {}).get("enabled", False):
            columns_to_preserve.update(
                ["Affectation (email)", "Affectation (nom)", "Entité Pilote"]
            )

        # Add similarity search columns
        if config.get("similarity_search", {}).get("enabled", False):
            columns_to_copy_config = config["similarity_search"].get(
                "columns_to_copy", {}
            )
            for column, col_config in columns_to_copy_config.items():
                if col_config.get("enabled", False):
                    columns_to_preserve.add(column)

        if config.get("default_opinion", False):
            columns_to_preserve.add("Avis du Gouvernement")

        # Preserve original values where they exist
        for column in columns_to_preserve:

            def preserve_original_value(row, col=column):
                matches = original_df.loc[
                    original_df["amdt_idx"] == row["amdt_idx"], col
                ]
                original_value = matches.iloc[0] if len(matches) > 0 else None
                return (
                    original_value
                    if pd.notna(original_value) and original_value not in [None, ""]
                    else row[col]
                )

            result_df[column] = result_df.apply(preserve_original_value, axis=1)

        return result_df

    def _populate_allotment_results(
        self,
        result_df: pd.DataFrame,
        original_df: pd.DataFrame,
        allotted_clusters: dict[tuple, list[list[int]]],
    ) -> pd.DataFrame:
        """
        Populate allotment results to the original dataframe.

        This is a special case because allotment changes the structure,
        so we need to propagate results back to filtered amendments.
        """
        if original_df is None:
            return result_df

        from graal.allotment.allotment_handler import AllotmentHandler

        # Columns that should be copied from processed amendments to allotted ones
        columns_to_copy = [
            "Réponse",
            "Sort",
            "Commentaires",
            "Objet amdt",
            "Avis du Gouvernement",
            "Affectation (email)",
            "Affectation (nom)",
            "Entité Pilote",
        ]

        result_df = AllotmentHandler.populate(
            original_amendments_df=original_df,
            pipeline_result_amdt_df=result_df,
            allotted_amdt_clusters=allotted_clusters,
            columns_to_copy=columns_to_copy,
        )

        return result_df

    def _save_results(self, result_df: pd.DataFrame, config: dict[str, Any]) -> None:
        """Save results to Excel and CSV files."""
        # Format output file prefix with current date (path is already preprocessed)
        output_file_prefix = datetime.now().strftime(
            config["output"]["file_prefix_template"]
        )

        # Get columns to output
        columns_to_output = config["output"]["columns"]

        # Save files
        result_df.to_excel(f"{output_file_prefix}.xlsx", columns=columns_to_output)
        result_df.to_csv(
            f"{output_file_prefix}.csv", sep=";", encoding="utf-8-sig", index=False
        )

        logging.info(
            f"Saved results to: {output_file_prefix}.xlsx and {output_file_prefix}.csv"
        )

    def _log_processing_summary(self, metadata: dict[str, Any]) -> None:
        """Log a summary of the processing."""
        logging.info("Processing Summary:")

        # Log preprocessing results
        for step_name, step_metadata in metadata.items():
            if (
                isinstance(step_metadata, dict)
                and "processed_amendments" in step_metadata
            ):
                logging.info(f"  {step_name}: {step_metadata}")

        # Log allotment results if available
        allotment_meta = metadata.get("allotment", {})
        if allotment_meta:
            logging.info(
                f"  Allotment: {allotment_meta.get('original_amendment_count', 0)} -> "
                f"{allotment_meta.get('filtered_amendment_count', 0)} amendments "
                f"(removed {allotment_meta.get('removed_amendment_count', 0)})"
            )
