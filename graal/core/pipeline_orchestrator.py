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

        1. Run preprocessing features (allotment) that can filter data
        2. Run regular features in parallel/any order
        3. Merge results

        Args:
            amendments_df: Original clean amendments data
            config: Full pipeline configuration

        Returns:
            Tuple of final processed DataFrame and processing outputs
        """
        # Keep original for reference
        processing_outputs = {}

        # Phase 1: Run preprocessing features (allotment, etc.)
        current_df = amendments_df.copy()
        for feature in self.preprocessing_features:
            if not feature.is_enabled(config):
                continue
            try:
                feature_input = FeatureInput(
                    amendments_df=current_df,
                    config=config,
                )
                feature.validate_input(feature_input)
                feature_output = feature.process(feature_input)
                # For preprocessing features, the filtered dataset becomes the new current_df
                current_df = feature_output.amendments_df.copy()
                processing_outputs[feature.feature_name] = feature_output.outputs
            except Exception as e:
                logging.error(
                    f"Preprocessing feature {feature.feature_name} failed: {str(e)}"
                )
                raise RuntimeError(
                    f"Pipeline failed during preprocessing feature {feature.feature_name}: {str(e)}"
                ) from e

        # Phase 2: Run features in parallel
        result_df = current_df

        # Get parallel processing configuration
        parallel_config = config.get("parallel_processing", {})
        max_workers = parallel_config.get("max_workers", 4)

        # Validate max_workers configuration
        if not isinstance(max_workers, int) or max_workers < 1:
            logging.warning(
                f"Invalid max_workers value: {max_workers}, defaulting to 1"
            )
            max_workers = 1

        # Filter enabled features
        enabled_features = [f for f in self.features if f.is_enabled(config)]

        if not enabled_features:
            return result_df, processing_outputs

        # Adjust max_workers to not exceed number of features
        max_workers = min(max_workers, len(enabled_features))

        logging.info(
            f"Processing {len(enabled_features)} features in parallel with {max_workers} workers"
        )

        # Process features in parallel
        feature_results = {}
        feature_timings = {}

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all features for processing
            future_to_feature = {}
            for feature in enabled_features:
                feature_input = FeatureInput(
                    amendments_df=current_df,  # Filtered by preprocessing
                    config=config,
                )

                future = executor.submit(
                    self._process_single_feature, feature, feature_input
                )
                future_to_feature[future] = feature

            # Collect results as they complete
            for future in as_completed(future_to_feature):
                feature = future_to_feature[future]
                try:
                    feature_output, processing_time = future.result()
                    feature_results[feature.feature_name] = feature_output
                    feature_timings[feature.feature_name] = processing_time
                    logging.info(
                        f"Feature '{feature.feature_name}' completed in {processing_time:.2f}s"
                    )
                except Exception as exc:
                    logging.error(
                        f"Feature '{feature.feature_name}' generated an exception: {exc}"
                    )
                    # Continue processing other features even if one fails
                    feature_results[feature.feature_name] = None
                    feature_timings[feature.feature_name] = 0.0

        # Merge all successful feature results
        for feature in enabled_features:
            feature_output = feature_results.get(feature.feature_name)
            if feature_output is not None:
                # Merge results - only update columns this feature owns
                result_df = self._merge_feature_results(
                    result_df, feature_output, feature.get_output_columns()
                )

                # Store feature outputs
                processing_outputs[feature.feature_name] = feature_output.outputs
            else:
                # Feature failed, store empty outputs
                processing_outputs[feature.feature_name] = {}

        # Log performance summary
        if feature_timings:
            total_time = sum(feature_timings.values())
            max_time = max(feature_timings.values())
            logging.info(
                f"Parallel processing completed. Total CPU time: {total_time:.2f}s, Wall time: {max_time:.2f}s"
            )
        else:
            logging.info("Parallel processing completed with no enabled features")

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

        try:
            feature.validate_input(feature_input)
            feature_output = feature.process(feature_input)
            processing_time = time.time() - start_time
            return feature_output, processing_time
        except Exception as e:
            processing_time = time.time() - start_time
            logging.error(f"Error processing feature '{feature.feature_name}': {e}")
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
        # Always use "amdt_idx" as index for merging
        base_df_indexed = base_df.set_index("amdt_idx")
        feature_output_df_indexed = feature_output.amendments_df.set_index("amdt_idx")

        # Update only the columns this feature is responsible for
        for col in output_columns:
            if col in feature_output_df_indexed.columns:
                if col in self.concatenated_columns:
                    # Concatenate values for configured columns
                    base_df_indexed[col] = self._concatenate_column_values(
                        base_df_indexed.get(col),
                        feature_output_df_indexed[col],
                    )
                else:
                    # Overwrite for regular columns
                    base_df_indexed[col] = feature_output_df_indexed[col]

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
