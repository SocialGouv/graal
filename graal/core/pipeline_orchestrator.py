import logging
import logging.config
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, Optional, Set

import pandas as pd

from graal.core.feature_interface import (
    BaseFeature,
    FeatureInput,
    FeatureOutput,
)

logging.config.fileConfig("logging.conf")


class PipelineOrchestrator:
    """
    Orchestrates the processing pipeline with clear separation between
    preprocessing features (like allotment) and regular features.
    """

    def __init__(
        self,
        preprocessing_features: list[BaseFeature],
        features: list[BaseFeature],
        concatenated_columns: Set[str] = None,
        concatenated_column_separator: str = "\n",
    ):
        self.preprocessing_features = preprocessing_features
        self.features = features
        self.concatenated_columns = concatenated_columns or {"Commentaires"}
        self.concatenated_column_separator = concatenated_column_separator

    def process(  # noqa: C901
        self,
        amendments_df: pd.DataFrame,
        config: Dict[str, Any],
    ) -> tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Process the full pipeline.

        IMPORTANT: This method assumes that columns have already been cleared ONCE
        by ProcessingPipeline._determine_columns_to_clear() before features run.
        This orchestrator NEVER clears columns - it only merges feature results,
        using concatenation for configured columns (like "Commentaires").

        1. Run preprocessing features (allotment) that can filter data
        2. Run regular features in parallel/any order
        3. Merge results (with concatenation for configured columns)

        Args:
            amendments_df: Original clean amendments data (with columns already cleared)
            config: Full pipeline configuration

        Returns:
            Tuple of final processed DataFrame and processing outputs
        """
        logging.info(
            f"[ORCHESTRATOR] Starting pipeline processing with {len(amendments_df)} amendments"
        )

        # Keep original for reference
        processing_outputs = {}

        # Phase 1: Run preprocessing features (allotment, etc.)
        current_df = amendments_df.copy()
        logging.info(
            f"[ORCHESTRATOR] Phase 1: Processing {len(self.preprocessing_features)} preprocessing features"
        )

        for feature in self.preprocessing_features:
            if not feature.is_enabled(config):
                logging.debug(
                    f"[ORCHESTRATOR] Skipping disabled preprocessing feature: {feature.feature_name}"
                )
                continue

            logging.info(
                f"[ORCHESTRATOR] Starting preprocessing feature: {feature.feature_name}"
            )
            try:
                feature_input = FeatureInput(
                    amendments_df=current_df,
                    config=config,
                )
                feature.validate_input(feature_input)
                logging.debug(
                    f"[ORCHESTRATOR] Input validation passed for feature: {feature.feature_name}"
                )

                feature_output = feature.process(feature_input)
                # For preprocessing features, the filtered dataset becomes the new current_df
                original_count = len(current_df)
                current_df = feature_output.amendments_df.copy()
                new_count = len(current_df)

                logging.info(
                    f"[ORCHESTRATOR] Preprocessing feature completed: {feature.feature_name}, amendments: {original_count} -> {new_count}"
                )
                processing_outputs[feature.feature_name] = feature_output.outputs

            except Exception as e:
                logging.error(
                    f"[ORCHESTRATOR] Preprocessing feature {feature.feature_name} failed: {str(e)}",
                    exc_info=True,
                )
                raise RuntimeError(
                    f"Pipeline failed during preprocessing feature {feature.feature_name}: {str(e)}"
                ) from e

        # Phase 2: Run features in parallel
        result_df = current_df
        logging.info(
            f"[ORCHESTRATOR] Phase 2: Starting parallel processing with {len(current_df)} amendments"
        )

        # Get parallel processing configuration
        parallel_config = config.get("parallel_processing", {})
        max_workers = parallel_config.get("max_workers", 4)

        # Validate max_workers configuration
        if not isinstance(max_workers, int) or max_workers < 1:
            logging.warning(
                f"[ORCHESTRATOR] Invalid max_workers value: {max_workers}, defaulting to 1"
            )
            max_workers = 1

        # Filter enabled features
        enabled_features = [f for f in self.features if f.is_enabled(config)]
        disabled_features = [f for f in self.features if not f.is_enabled(config)]

        logging.info(
            f"[ORCHESTRATOR] Feature status - enabled: {len(enabled_features)}, disabled: {len(disabled_features)}"
        )
        for feature in enabled_features:
            logging.debug(f"[ORCHESTRATOR] Enabled feature: {feature.feature_name}")
        for feature in disabled_features:
            logging.debug(f"[ORCHESTRATOR] Disabled feature: {feature.feature_name}")

        if not enabled_features:
            logging.info(
                "[ORCHESTRATOR] No enabled features to process, returning preprocessed data"
            )
            return result_df, processing_outputs

        # Adjust max_workers to not exceed number of features
        max_workers = min(max_workers, len(enabled_features))

        logging.info(
            f"[ORCHESTRATOR] Processing {len(enabled_features)} features in parallel with {max_workers} workers"
        )

        # Process features in parallel
        feature_results = {}
        feature_timings = {}

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            logging.debug(
                f"[ORCHESTRATOR] Created ThreadPoolExecutor with {max_workers} workers"
            )

            # Submit all features for processing
            future_to_feature = {}
            for feature in enabled_features:
                feature_input = FeatureInput(
                    amendments_df=current_df,  # Filtered by preprocessing
                    config=config,
                )

                logging.debug(
                    f"[ORCHESTRATOR] Submitting feature for parallel processing: {feature.feature_name}"
                )
                future = executor.submit(
                    self._process_single_feature, feature, feature_input
                )
                future_to_feature[future] = feature

            logging.info(
                f"[ORCHESTRATOR] Submitted {len(future_to_feature)} features for parallel processing"
            )

            # Collect results as they complete
            completed_count = 0
            for future in as_completed(future_to_feature):
                feature = future_to_feature[future]
                completed_count += 1

                try:
                    feature_output, processing_time = future.result()
                    feature_results[feature.feature_name] = feature_output
                    feature_timings[feature.feature_name] = processing_time
                    logging.info(
                        f"[ORCHESTRATOR] Feature completed ({completed_count}/{len(enabled_features)}): '{feature.feature_name}' in {processing_time:.2f}s"
                    )
                except Exception as exc:
                    logging.error(
                        f"[ORCHESTRATOR] Feature failed ({completed_count}/{len(enabled_features)}): '{feature.feature_name}' - {exc}",
                        exc_info=True,
                    )
                    # Continue processing other features even if one fails
                    feature_results[feature.feature_name] = None
                    feature_timings[feature.feature_name] = 0.0

        # Merge all successful feature results
        logging.info("[ORCHESTRATOR] Starting result merging phase")
        successful_features = 0
        failed_features = 0

        for feature in enabled_features:
            feature_output = feature_results.get(feature.feature_name)
            if feature_output is not None:
                logging.debug(
                    f"[ORCHESTRATOR] Merging results for feature: {feature.feature_name}"
                )
                # Merge results - only update columns this feature owns
                result_df = self._merge_feature_results(
                    result_df, feature_output, feature.get_output_columns()
                )

                # Store feature outputs
                processing_outputs[feature.feature_name] = feature_output.outputs
                successful_features += 1
            else:
                # Feature failed, store empty outputs
                logging.warning(
                    f"[ORCHESTRATOR] Skipping merge for failed feature: {feature.feature_name}"
                )
                processing_outputs[feature.feature_name] = {}
                failed_features += 1

        # Log performance summary
        if feature_timings:
            total_time = sum(feature_timings.values())
            max_time = max(feature_timings.values())
            avg_time = total_time / len(feature_timings) if feature_timings else 0
            logging.info(
                f"[ORCHESTRATOR] Parallel processing completed - successful: {successful_features}, failed: {failed_features}"
            )
            logging.info(
                f"[ORCHESTRATOR] Performance summary - Total CPU time: {total_time:.2f}s, Wall time: {max_time:.2f}s, Avg time: {avg_time:.2f}s"
            )
        else:
            logging.info(
                "[ORCHESTRATOR] Parallel processing completed with no enabled features"
            )

        logging.info(
            f"[ORCHESTRATOR] Pipeline processing completed - final amendments: {len(result_df)}"
        )
        return result_df, processing_outputs

    def _process_single_feature(
        self, feature: BaseFeature, feature_input: FeatureInput
    ) -> tuple[FeatureOutput, float]:
        """
        Process a single feature and measure execution time.

        Args:
            feature: The feature to process
            feature_input: Input data for the feature

        Returns:
            Tuple of (feature_output, processing_time_in_seconds)
        """
        start_time = time.time()
        logging.debug(
            f"[ORCHESTRATOR] Starting single feature processing: {feature.feature_name}"
        )

        try:
            logging.debug(
                f"[ORCHESTRATOR] Validating input for feature: {feature.feature_name}"
            )
            feature.validate_input(feature_input)

            logging.debug(f"[ORCHESTRATOR] Processing feature: {feature.feature_name}")
            feature_output = feature.process(feature_input)

            processing_time = time.time() - start_time
            logging.debug(
                f"[ORCHESTRATOR] Feature processing completed: {feature.feature_name} in {processing_time:.2f}s"
            )
            return feature_output, processing_time
        except Exception as e:
            processing_time = time.time() - start_time
            logging.error(
                f"[ORCHESTRATOR] Error processing feature '{feature.feature_name}' after {processing_time:.2f}s: {e}",
                exc_info=True,
            )
            raise

    def _merge_feature_results(
        self,
        base_df: pd.DataFrame,
        feature_output: FeatureOutput,
        output_columns: Set[str],
    ) -> pd.DataFrame:
        """
        Merge feature results back into the base DataFrame.

        Only merge the columns that the feature is supposed to output.
        For columns in concatenated_columns, concatenate values instead of overwriting.
        """
        logging.debug(
            f"[ORCHESTRATOR] Merging feature results - output_columns: {output_columns}"
        )

        # Always use "amdt_idx" as index for merging
        base_df_indexed = base_df.set_index("amdt_idx")
        feature_output_df_indexed = feature_output.amendments_df.set_index("amdt_idx")

        logging.debug(
            f"[ORCHESTRATOR] Merge setup - base_df rows: {len(base_df_indexed)}, feature_output rows: {len(feature_output_df_indexed)}"
        )

        # Update only the columns this feature is responsible for
        merged_columns = []
        concatenated_columns = []

        for col in output_columns:
            if col in feature_output_df_indexed.columns:
                if col in self.concatenated_columns:
                    # Concatenate values for configured columns
                    logging.debug(f"[ORCHESTRATOR] Concatenating column: {col}")
                    base_df_indexed[col] = self._concatenate_column_values(
                        base_df_indexed.get(col),
                        feature_output_df_indexed[col],
                    )
                    concatenated_columns.append(col)
                else:
                    # Overwrite for regular columns
                    logging.debug(f"[ORCHESTRATOR] Overwriting column: {col}")
                    base_df_indexed[col] = feature_output_df_indexed[col]
                    merged_columns.append(col)
            else:
                logging.debug(
                    f"[ORCHESTRATOR] Column not found in feature output: {col}"
                )

        logging.debug(
            f"[ORCHESTRATOR] Merge completed - merged: {merged_columns}, concatenated: {concatenated_columns}"
        )
        return base_df_indexed.reset_index()

    # Create a function to concatenate individual values
    def _concatenate_values(self, base_val: Optional[str], feature_val: Optional[str]):
        # Convert to strings and handle null/empty values
        base_str = str(base_val) if pd.notna(base_val) and base_val != "" else ""
        feature_str = (
            str(feature_val) if pd.notna(feature_val) and feature_val != "" else ""
        )

        # If both are empty, return empty string
        if not base_str and not feature_str:
            return ""

        # If only one has content, return that one
        if not base_str:
            return feature_str
        if not feature_str:
            return base_str

        # Both have content, concatenate with separator
        return f"{base_str}{self.concatenated_column_separator}{feature_str}"

    def _concatenate_column_values(
        self,
        base_series: pd.Series,
        feature_series: pd.Series,
    ) -> pd.Series:
        """
        Concatenate values from base and feature series, handling null/empty values.

        Args:
            base_series: Existing values in the base DataFrame (may be None if column doesn't exist)
            feature_series: New values from the feature

        Returns:
            Series with concatenated values
        """
        # If base_series is None (column doesn't exist yet), use feature_series directly
        if base_series is None:
            return feature_series

        # Apply concatenation element-wise, aligning by index
        result = pd.Series(index=feature_series.index, dtype=str)
        for idx in feature_series.index:
            base_val = base_series.get(idx) if idx in base_series.index else ""
            feature_val = feature_series.get(idx)
            result[idx] = self._concatenate_values(base_val, feature_val)

        return result
