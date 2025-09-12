import logging
import logging.config
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

    def process(
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

            feature_input = FeatureInput(
                amendments_df=current_df,
                config=config,
            )

            feature.validate_input(feature_input)
            feature_output = feature.process(feature_input)

            # For preprocessing features, the filtered dataset becomes the new current_df
            current_df = feature_output.amendments_df.copy()
            processing_outputs[feature.feature_name] = feature_output.outputs

        # Phase 2: Run features
        result_df = current_df.copy()

        for feature in self.features:
            if not feature.is_enabled(config):
                continue

            # Each feature gets the filtered data from preprocessing
            # but processes independently
            feature_input = FeatureInput(
                amendments_df=current_df,  # Filtered by preprocessing
                config=config,
            )

            feature.validate_input(feature_input)
            feature_output = feature.process(feature_input)

            # Merge results - only update columns this feature owns
            result_df = self._merge_feature_results(
                result_df, feature_output, feature.get_output_columns()
            )

            # Store feature outputs
            processing_outputs[feature.feature_name] = feature_output.outputs

        return result_df, processing_outputs

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
