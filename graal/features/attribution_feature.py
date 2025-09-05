"""
Attribution feature implementation.

This feature assigns amendments to reviewers.
"""

import logging
import logging.config
from typing import Any, Set

import pandas as pd

from graal.attribution.project_configurations import (
    get_attribution_handler_builder_func,
)
from graal.core.feature_interface import (
    BaseFeature,
    FeatureInput,
    FeatureOutput,
)
from graal.core.text_normalizers import TextNormalizerFactory

logging.config.fileConfig("logging.conf")


class AttributionFeature(BaseFeature):
    """
    Processes amendments to determine appropriate reviewers
    without affecting the original data or other features.
    """

    def __init__(self, config_excel: dict[str, pd.DataFrame] = None):
        super().__init__("attribution")
        self.normalizer = TextNormalizerFactory.get_normalizer("attribution")
        self.config_excel = config_excel

    def get_required_columns(self) -> Set[str]:
        """Attribution requires corps and expose columns."""
        return {
            "Corps amdt",
            "Exposé amdt",
            "amdt_idx",
        }

    def get_output_columns(self) -> Set[str]:
        """Attribution produces these columns."""
        return {
            "Affectation (email)",
            "Affectation (nom)",
            "Entité Pilote",
            "Commentaires",
        }

    def is_enabled(self, config: dict[str, Any]) -> bool:
        """Check if attribution is enabled."""
        return config.get("attribution", {}).get("enabled", False)

    def process(self, feature_input: FeatureInput) -> FeatureOutput:
        """
        Process amendments for attribution.

        This creates its own normalized text internally without
        affecting the input data.
        """
        # Work with our own copy
        working_df = feature_input.amendments_df.copy()
        config = feature_input.config.get("attribution", {})

        # Create normalized columns for internal processing only
        working_df = self._normalize_text_columns(working_df)

        # Load configuration data
        if self.config_excel is None:
            raise ValueError("Attribution feature requires config_excel parameter")

        # Get project configuration
        project_name = config.get("project_name", "PLF")
        builder_func = get_attribution_handler_builder_func(project_name)
        attribution_handler = builder_func(self.config_excel)

        # Process attributions
        result_df = attribution_handler.process_amendments(working_df)
        result_df.set_index("amdt_idx", inplace=True)

        # Copy output columns to a clean version of the original data
        output_columns = self.get_output_columns()
        final_df = feature_input.amendments_df.copy()

        # Ensure result_df index aligns with final_df for column assignment
        for col in output_columns:
            if col in result_df.columns:
                final_df.loc[result_df.index, col] = result_df[col]

        return FeatureOutput(
            amendments_df=final_df,
            outputs={
                "processed_amendments": len(result_df),
                "attribution_method": project_name,
            },
        )

    def _normalize_text_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Create normalized text columns for internal processing.

        These are temporary columns that won't affect the output.
        """
        # Create normalized versions for attribution processing
        df.loc[:, "Corps amdt"] = df["Corps amdt"].apply(
            lambda x: self.normalizer.normalize_for_feature(str(x))
        )

        df.loc[:, "Exposé amdt"] = df["Exposé amdt"].apply(
            lambda x: self.normalizer.normalize_for_feature(str(x))
        )

        return df
