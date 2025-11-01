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
from graal.utils.sheet_data_loader import SheetDataLoader
from graal.utils.text_utils import (
    add_placeholders_to_empty_column,
)

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
        logging.info("[PIPELINE] Starting pipeline processing")
        start_time = time.time()

        # Phase 0: Preprocess configuration (resolve environment variables, validate paths)
        logging.info("[PIPELINE] Phase 0: Preprocessing configuration")
        config_preprocessor = ConfigPreprocessor(
            validate_paths=False
        )  # Don't validate paths that might not exist yet
        preprocessed_config = config_preprocessor.preprocess_config(config)
        logging.debug("[PIPELINE] Configuration preprocessing completed")

        # Phase 1: Load and prepare data
        logging.info("[PIPELINE] Phase 1: Loading and preparing data")
        amendments_df, dependencies = self._load_and_prepare_data(preprocessed_config)
        # amendments_df = amendments_df[amendments_df["Num amdt"].isin([281, 829, 1207])]
        # logging.warning(f"amendments_df {amendments_df}")

        logging.info(
            f"[PIPELINE] Data loading completed - amendments: {len(amendments_df)}"
        )

        # Store preprocessed original dataframe for allotment population (before clearing)
        dependencies["preprocessed_original_df"] = amendments_df.copy()
        logging.debug(
            "[PIPELINE] Stored preprocessed original dataframe for allotment population"
        )

        # Phase 2: Get features from dependencies (already created during data preparation)
        # NOTE: Column clearing happens in _load_and_prepare_data() via _determine_columns_to_clear()
        # This clearing happens ONCE at the very beginning, before any features run.
        # After clearing, each feature receives a clean copy to work with, and the orchestrator
        # merges results (with concatenation for configured columns like "Commentaires").
        preprocessing_features = dependencies["preprocessing_features"]
        features = dependencies["features"]
        logging.info(
            f"[PIPELINE] Phase 2: Feature setup - preprocessing: {len(preprocessing_features)}, regular: {len(features)}"
        )

        # Phase 3: Run orchestrated processing
        # Features run in parallel and write to their own copies. The orchestrator then
        # merges results, using concatenation for configured columns (like "Commentaires").
        logging.info("[PIPELINE] Phase 3: Starting orchestrated processing")
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
        logging.info(
            f"[PIPELINE] Orchestrated processing completed - result amendments: {len(result_df)}"
        )

        # Phase 4: Handle special post-processing and output
        logging.info("[PIPELINE] Phase 4: Finalizing and generating output")
        self._finalize_and_output(
            result_df, preprocessed_config, dependencies, processing_outputs
        )

        end_time = time.time()
        logging.info(
            f"[PIPELINE] Pipeline processing completed in {end_time - start_time:.2f} seconds"
        )

    def _load_and_prepare_data(
        self, config: dict[str, Any]
    ) -> tuple[pd.DataFrame, dict[str, Any]]:
        """
        Load and prepare data for processing and create dependency objects.

        This handles the initial data loading and basic cleaning that
        all features need, without feature-specific normalization.
        """
        logging.info("[PIPELINE] Starting data loading and preparation")

        DATA_FOLDER = os.environ["DATA_FOLDER"]
        logging.debug(f"[PIPELINE] Using DATA_FOLDER: {DATA_FOLDER}")

        # Load configuration Excel file (path is already preprocessed)
        graal_config_file = Path(config["paths"]["graal_config_file"])
        logging.info(
            f"[PIPELINE] Loading configuration Excel file: {graal_config_file}"
        )

        # Use SheetDataLoader which supports both S3 and local files
        sheet_loader = SheetDataLoader(graal_config_file)
        config_excel = sheet_loader.excel_data
        logging.debug(
            f"[PIPELINE] Configuration Excel loaded - sheets: {list(config_excel.keys())}"
        )

        # Build input files configuration
        logging.debug("[PIPELINE] Building input files configuration")
        input_files_config = self._build_input_files_config(config)
        logging.info(
            f"[PIPELINE] Input files configuration built - files: {len(input_files_config)}"
        )

        # Load amendments from input files
        logging.info("[PIPELINE] Loading amendments from input files")
        amendments_df = self._load_amendments(input_files_config)
        logging.info(
            f"[PIPELINE] Amendments loaded - count: {len(amendments_df)}, columns: {len(amendments_df.columns)}"
        )

        # Apply mission filter if specified
        if config.get("mission_short_title_filter"):
            original_count = len(amendments_df)
            logging.info(
                f"[PIPELINE] Applying mission filter: {config['mission_short_title_filter']}"
            )
            amendments_df = self._apply_mission_filter(
                amendments_df, config["mission_short_title_filter"]
            )
            logging.info(
                f"[PIPELINE] Mission filter applied - amendments: {original_count} -> {len(amendments_df)}"
            )

        # Handle placeholder amendment bodies if enabled
        if config.get("processing_options", {}).get("placeholder_amdt_body", False):
            logging.info("[PIPELINE] Adding placeholder amendment bodies")
            amendments_df = self._add_placeholder_bodies(amendments_df)
            logging.debug("[PIPELINE] Placeholder bodies added")

        # Load and apply basic preprocessing (not feature-specific)
        logging.info("[PIPELINE] Starting basic preprocessing")
        acronym_mapping = AmendmentPreProcessor.load_acronyms(config_excel["Acronymes"])
        logging.debug(
            f"[PIPELINE] Acronym mapping loaded - entries: {len(acronym_mapping)}"
        )

        # Drop empty rows and replace acronyms
        original_count = len(amendments_df)
        amendments_df = AmendmentPreProcessor.drop_empty_rows_in_columns(
            amendments_df=amendments_df,
            columns_to_filter=["Exposé amdt"],
        )
        logging.info(
            f"[PIPELINE] Empty rows dropped - amendments: {original_count} -> {len(amendments_df)}"
        )

        # Apply universal preprocessing (acronym replacement + gage sentence removal)
        logging.debug("[PIPELINE] Applying universal preprocessing")
        amendments_df = AmendmentPreProcessor.apply_universal_preprocessing(
            amendments_df=amendments_df,
            acronym_mapping=acronym_mapping,
            columns_to_process=["Corps amdt", "Exposé amdt"],
        )
        logging.debug("[PIPELINE] Universal preprocessing complete")

        # Handle common amendment patterns
        logging.debug("[PIPELINE] Handling common amendment patterns")
        amendments_df = (
            AmendmentPreProcessor.handle_common_amendment_expose_and_redactional(
                amendments_df=amendments_df, add_redactional_column=True
            )
        )
        logging.debug("[PIPELINE] Common amendment patterns processed")

        # Create LLM clients for summary generation
        logging.info("[PIPELINE] Creating LLM clients for summary generation")
        # Extract credentials if provided from frontend (stored in llm_credentials)
        credentials = config.get("llm_credentials", None)
        llm_api_clients = create_llm_api_clients(config, credentials=credentials)
        rate_limiting_config = get_rate_limiting_config(config)
        summary_gen_load_balancer = SummaryGenerationLoadBalancer(
            clients=llm_api_clients,
            queue_timeout=4,
            max_retries=5,
            rate_limiting_config=rate_limiting_config,
        )
        logging.debug(
            f"[PIPELINE] LLM load balancer created - clients: {len(llm_api_clients)}"
        )

        # Create all features to determine columns to clear
        logging.info("[PIPELINE] Creating feature instances")
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
        logging.info(
            f"[PIPELINE] Features created - preprocessing: {len(preprocessing_features)}, regular: {len(features)}"
        )

        # Clear columns that will be overridden by features
        logging.info("[PIPELINE] Determining columns to clear")
        columns_to_clear = self._determine_columns_to_clear(config, all_features)
        logging.info(f"[PIPELINE] Columns to clear: {columns_to_clear}")

        amendments_df = AmendmentPreProcessor.clear_columns_to_be_overridden(
            amendments_df=amendments_df, columns_to_clear=columns_to_clear
        )
        logging.debug("[PIPELINE] Columns cleared for feature processing")

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

        logging.info(
            f"[PIPELINE] Data loading and preparation completed - final amendments: {len(amendments_df)}"
        )

        # For testing purposes
        # amendments_df = amendments_df[
        #     amendments_df["Num amdt"].isin([2342, 2089, 2382])
        # ]

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
        logging.info(
            f"[PIPELINE] Loading amendments from file: {file_path} (type: {suffix})"
        )

        if suffix in [".xlsx", ".xls"]:
            logging.debug("[PIPELINE] Using Excel loader")
            amendments_df = AmendmentPreProcessor.load_amendments_excel(
                [file_path], input_files_config
            )
        elif suffix == ".json":
            logging.debug("[PIPELINE] Using JSON loader")
            amendments_df = AmendmentPreProcessor.load_amendments_json(
                [file_path], input_files_config
            )
        else:
            logging.error(f"[PIPELINE] Unsupported file type: {suffix}")
            raise ValueError(f"Unsupported file type: {suffix}")

        logging.info(
            f"[PIPELINE] Amendments loaded successfully - count: {len(amendments_df)}"
        )
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
                lambda x: any(mission in x for mission in mission_filters)
            )
        ]
        return amendments_df

    def _add_placeholder_bodies(self, amendments_df: pd.DataFrame) -> pd.DataFrame:
        """Add placeholder bodies for empty amendments with indexed placeholders."""
        return add_placeholders_to_empty_column(
            df=amendments_df,
            column="Corps amdt",
            placeholder_generator=lambda idx, row: (
                f"Ce corps d'amendement peut être ignoré, il a été ajouté pour faciliter le traitement des amendements {idx}"
            ),
        )

    def _determine_columns_to_clear(
        self, config: dict[str, Any], all_features: list[BaseFeature]
    ) -> set[str]:
        """
        Determine which columns should be cleared based on enabled features.

        Clearing happens ONCE at the very beginning of processing, before any features run.
        This removes old data from previous runs. After clearing, features write their data,
        and the orchestrator merges results (with concatenation for configured columns).
        """
        columns_to_clear = {"Commentaires"}  # Always clear comments

        # Get columns to clear from all features, respecting overwrite settings
        for feature in all_features:
            if not feature.is_enabled(config):
                continue

            # Get the feature-specific config
            feature_name = feature.feature_name
            feature_config = config.get(feature_name, {})

            # Only clear columns if the feature will actually overwrite them
            if feature_config.get("should_overwrite", True):
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
        logging.info(
            f"[PIPELINE] Starting finalization with {len(result_df)} amendments"
        )

        # Handle allotment result population (special case since allotment affects structure)
        allotment_outputs = processing_outputs.get("allotment", {})
        if allotment_outputs and "allotted_clusters" in allotment_outputs:
            logging.info(
                "[PIPELINE] Populating allotment results to original dataframe"
            )
            original_count = len(result_df)
            result_df = self._populate_allotment_results(
                result_df,
                dependencies.get("preprocessed_original_df"),
                allotment_outputs["allotted_clusters"],
            )
            logging.info(
                f"[PIPELINE] Allotment population completed - amendments: {original_count} -> {len(result_df)}"
            )

        # Generate output files
        logging.info("[PIPELINE] Generating output files")
        self._save_results(result_df, config)

        # Log processing summary
        logging.info("[PIPELINE] Generating processing summary")
        self._log_processing_summary(processing_outputs)

        logging.info("[PIPELINE] Finalization completed")

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
        logging.info(f"[PIPELINE] Saving results with prefix: {output_file_prefix}")

        # Get columns to output
        columns_to_output = config["output"]["columns"]
        logging.debug(
            f"[PIPELINE] Output columns configured: {len(columns_to_output)} columns"
        )

        # Defensive programming: filter out columns that don't exist in result_df
        available_columns = result_df.columns.tolist()
        existing_columns = [
            col for col in columns_to_output if col in available_columns
        ]
        missing_columns = [
            col for col in columns_to_output if col not in available_columns
        ]

        if missing_columns:
            logging.warning(
                f"[PIPELINE] Some configured output columns are not present in result DataFrame. "
                f"Missing columns: {missing_columns}. "
                f"Using {len(existing_columns)}/{len(columns_to_output)} configured columns."
            )

        # Use filtered columns for output
        columns_to_use = existing_columns

        # Save files
        try:
            excel_path = f"{output_file_prefix}.xlsx"
            csv_path = f"{output_file_prefix}.csv"

            result_df.to_excel(excel_path, columns=columns_to_use)

            csv_separator = config["output"].get("csv_separator", ";")
            result_df.to_csv(
                csv_path,
                sep=csv_separator,
                encoding="utf-8-sig",
                index=False,
            )

            # Log file sizes
            try:
                excel_size = Path(excel_path).stat().st_size
                csv_size = Path(csv_path).stat().st_size
                logging.info(
                    f"[PIPELINE] Results saved successfully - Excel: {excel_path} ({excel_size} bytes), CSV: {csv_path} ({csv_size} bytes)"
                )
            except Exception as e:
                logging.warning(f"[PIPELINE] Could not get file sizes: {str(e)}")
                logging.info(
                    f"[PIPELINE] Results saved successfully - Excel: {excel_path}, CSV: {csv_path}"
                )

        except Exception as e:
            logging.error(f"[PIPELINE] Failed to save results: {str(e)}", exc_info=True)
            raise

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
