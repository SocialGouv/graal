"""
Summary generation feature implementation.

This feature generates summaries for amendments.
"""

import logging
import logging.config
import re
from typing import Any, Set

import pandas as pd

from graal.core.feature_interface import BaseFeature, FeatureInput, FeatureOutput
from graal.summary.summary_generation_load_balancer import SummaryGenerationLoadBalancer
from graal.summary.summary_handler import SummaryHandler

logging.config.fileConfig("logging.conf")


class SummaryGenerationFeature(BaseFeature):
    """
    Generates summaries for amendments.
    """

    def __init__(
        self,
        summary_gen_load_balancer: SummaryGenerationLoadBalancer = None,
        acronym_mapping: dict = None,
        config_excel: dict[str, pd.DataFrame] = None,
    ):
        super().__init__("summary_generation")
        self.summary_gen_load_balancer = summary_gen_load_balancer
        self.acronym_mapping = acronym_mapping or {}
        self.config_excel = config_excel

    def get_required_columns(self) -> Set[str]:
        """Summary generation requires these columns."""
        return {"Corps amdt", "Exposé amdt", "amdt_idx", "Objet amdt"}

    def get_output_columns(self) -> Set[str]:
        """Summary generation produces these columns."""
        return {"Objet amdt"}

    def is_enabled(self, config: dict[str, Any]) -> bool:
        """Check if summary generation is enabled."""
        return config.get("summary_generation", {}).get("enabled", False)

    def get_columns_to_clear(self, config: dict[str, Any]) -> Set[str]:
        """Return columns to clear if summary generation is enabled."""
        if self.is_enabled(config):
            return {"Objet amdt"}
        return set()

    def process(self, feature_input: FeatureInput) -> FeatureOutput:
        """
        Process amendments for summary generation.

        This creates its own normalized text internally without
        affecting the input data.
        """
        # Work with our own copy
        working_df = feature_input.amendments_df.copy()
        summary_config = feature_input.config.get("summary_generation", {})
        should_overwrite = summary_config.get("should_overwrite", True)

        # Validate required dependencies
        if not self.summary_gen_load_balancer:
            raise ValueError(
                "Summary feature requires summary_gen_load_balancer parameter"
            )
        if not self.config_excel:
            raise ValueError("Summary feature requires config_excel parameter")

        # Get the prompt configuration - ensure it's a string, not a pandas object
        prompt_series = self.config_excel["Prompt Objet"]
        if not prompt_series.empty:
            # Extract the actual value from pandas - .values[0] gets the raw Python value
            config_prompt = prompt_series.values[0]
            # Ensure it's a string
            if not isinstance(config_prompt, str):
                config_prompt = str(config_prompt)
        else:
            config_prompt = ""

        # Create summary handler with our working copy
        summary_handler = SummaryHandler(
            summary_gen_load_balancer=self.summary_gen_load_balancer,
            amendments_df=working_df,
            acronym_mapping=self.acronym_mapping,
            summary_column="Objet amdt",
            config_prompt=config_prompt,
            should_overwrite=should_overwrite,
        )

        # Process summaries
        result_df = summary_handler.populate()
        result_df.set_index("amdt_idx", inplace=True)

        # Handle "amendements d'appel" pattern
        result_df = self._handle_amendements_appel(result_df)

        # Create final result - copy only the summary column
        final_df = feature_input.amendments_df.copy()
        final_df["Objet amdt"] = result_df["Objet amdt"]

        return FeatureOutput(
            amendments_df=final_df,
            outputs={
                "processed_amendments": len(result_df),
                "summaries_generated": len(result_df[result_df["Objet amdt"].notna()]),
            },
        )

    def _handle_amendements_appel(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Handle the special case of 'amendements d'appel'.

        This adds the 'APPEL :' prefix to certain amendments.
        """
        regex_pattern = r"amendements? d.?appel"
        mask = df["Exposé amdt"].apply(
            lambda x: isinstance(x, str)
            and re.search(regex_pattern, x, re.IGNORECASE) is not None
        ) & (df["Objet amdt"] != "Supprimer cet article.")

        df.loc[mask, "Objet amdt"] = "APPEL : " + df.loc[mask, "Objet amdt"]

        return df
