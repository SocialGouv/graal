"""
Default opinion feature implementation.

This feature sets a default opinion for amendments based on the author's group.
"""

from typing import Any, Set

import pandas as pd

from graal.attribution.attribution_data_loader import AttributionDataLoader
from graal.core.feature_interface import BaseFeature, FeatureInput, FeatureOutput
from graal.opinion.opinion_handler import OpinionHandler


class OpinionFeature(BaseFeature):
    """
    Assigns default opinions to amendments.
    """

    def __init__(self, config_excel: dict[str, pd.DataFrame]):
        super().__init__("default_opinion")
        self.config_excel = config_excel

    def get_required_columns(self) -> Set[str]:
        """Opinion feature requires these columns."""
        return {
            "amdt_idx",
            "Affectation (nom)",  # Depends on attribution results
        }

    def get_output_columns(self) -> Set[str]:
        """Opinion feature produces this column."""
        return {"Avis du Gouvernement"}

    def is_enabled(self, config: dict[str, Any]) -> bool:
        """Check if default opinion is enabled."""
        return config.get("default_opinion", False)

    def process(self, feature_input: FeatureInput) -> FeatureOutput:
        """
        Process amendments for default opinion assignment.
        """

        # Work with our own copy
        working_df = feature_input.amendments_df.copy()

        # Get required configuration
        if not self.config_excel:
            raise ValueError("Opinion feature requires config_excel parameter")

        # Load opinion mappings
        group_to_default_opinion = AttributionDataLoader.load_group_to_default_opinion(
            self.config_excel
        )

        # Create opinion handler
        opinion_handler = OpinionHandler(
            amendments_df=working_df,
            group_to_default_opinion=group_to_default_opinion,
        )

        # Process opinions
        result_df = opinion_handler.populate()
        result_df = result_df.set_index("amdt_idx")

        # Handle allotment consistency (if allotment column exists)
        if "Allotissement" in result_df.columns:
            result_df = self._handle_allotment_opinion_consistency(result_df)

        # Create final result with proper alignment
        final_df = feature_input.amendments_df.copy()
        # Use merge to ensure proper alignment
        opinion_mapping = result_df["Avis du Gouvernement"]
        final_df["Avis du Gouvernement"] = final_df.index.map(opinion_mapping)

        return FeatureOutput(
            amendments_df=final_df,
            outputs={
                "processed_amendments": len(result_df),
                "opinions_assigned": len(
                    result_df[result_df["Avis du Gouvernement"].notna()]
                ),
            },
        )

    def _handle_allotment_opinion_consistency(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Ensure opinion consistency within allotment groups.

        If any amendment in an allotment has "Défavorable", all should have it.
        """
        if "Allotissement" not in df.columns:
            return df

        # Collect allotments that need to be set to "Défavorable"
        allotments_to_update = []
        for allot, group in df.groupby("Allotissement"):
            if "Défavorable" in group["Avis du Gouvernement"].values:
                allotments_to_update.append(allot)

        # Apply updates after iteration
        for allot in allotments_to_update:
            df.loc[
                df["Allotissement"] == allot,
                "Avis du Gouvernement",
            ] = "Défavorable"

        return df
