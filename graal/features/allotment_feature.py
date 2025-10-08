"""
Allotment feature implementation.

This feature filters duplicate amendments based on similarity analysis.
"""

import logging
import logging.config
from typing import Any

import pandas as pd

from graal.allotment.allotment_handler import AllotmentHandler
from graal.attribution.attribution_data_loader import AttributionDataLoader
from graal.core.feature_interface import (
    BaseFeature,
    FeatureInput,
    FeatureOutput,
)
from graal.core.text_normalizers import TextNormalizerFactory
from graal.utils.amendment_pre_processor import AmendmentPreProcessor

logging.config.fileConfig("logging.conf")


class AllotmentFeature(BaseFeature):
    """
    Allotment feature that filters duplicate amendments.

    This feature removes duplicate amendments based on similarity analysis.
    It's registered as a preprocessing feature to run before other features.
    """

    def __init__(self, config_excel: dict[str, pd.DataFrame] = None):
        super().__init__("allotment")
        self.normalizer = TextNormalizerFactory.get_normalizer("allotment")
        self.config_excel = config_excel

    def get_required_columns(self) -> set[str]:
        """Allotment requires corps and expose columns for similarity analysis."""
        return {
            "Corps amdt",
            "Exposé amdt",
            "Num article",
            "amdt_idx",
        }

    def get_output_columns(self) -> set[str]:
        """Allotment produces allotment column."""
        return {"Allotissement"}

    def is_enabled(self, config: dict[str, Any]) -> bool:
        """Check if allotment is enabled."""
        return config.get("allotments", {}).get("enabled", False)

    def get_columns_to_clear(self, config: dict[str, Any]) -> set[str]:
        """Return columns to clear if allotment is enabled."""
        if self.is_enabled(config):
            return {"Allotissement"}
        return set()

    def process(self, feature_input: FeatureInput) -> FeatureOutput:
        """
        Process allotments - filter duplicate amendments.

        This feature filters the dataset by removing duplicate amendments,
        which affects downstream feature processing.
        """

        # Work with our own copy
        working_df = feature_input.amendments_df.copy()
        config = feature_input.config

        allotment_config = config.get("allotments", {})
        allotment_column = allotment_config.get("column", "Corps amdt")
        similarity_threshold = allotment_config.get("similarity_threshold", 0.999)
        tf_idf_threshold = config.get("similarity_thresholds", {}).get(
            "tf_idf_threshold", 0.4
        )

        # Load acronym mapping if available
        acronym_mapping = None
        if self.config_excel and "Acronymes" in self.config_excel:
            acronym_mapping = AmendmentPreProcessor.load_acronyms(
                self.config_excel["Acronymes"]
            )

        # Get attribution-based removal strategy if attribution is enabled
        removal_strategy_func = AllotmentHandler.default_removal_strategy_func

        if config.get("attribution", {}).get("enabled", False):
            # Build attribution-aware removal strategy
            if self.config_excel:
                default_attributions = (
                    AttributionDataLoader.load_default_attribution_mappings(
                        self.config_excel
                    )
                )
                removal_strategy_func = self._build_attribution_aware_removal_strategy(
                    default_attributions
                )

        # Process allotments
        filtered_df, allotted_clusters = AllotmentHandler.process_allotments(
            amendments_df=working_df,
            allotment_column=allotment_column,
            similarity_threshold=similarity_threshold,
            group_by_columns=["Num article"],
            eps=tf_idf_threshold,
            acronym_mapping=acronym_mapping,
            removal_strategy_func=removal_strategy_func,
        )

        # Create metadata about what was filtered
        original_count = len(working_df)
        filtered_count = len(filtered_df)
        removed_count = original_count - filtered_count

        outputs = {
            "original_amendment_count": original_count,
            "filtered_amendment_count": filtered_count,
            "removed_amendment_count": removed_count,
            "allotted_clusters": allotted_clusters,
            "similarity_threshold": similarity_threshold,
        }

        return FeatureOutput(
            amendments_df=filtered_df,
            outputs=outputs,
        )

    def _build_attribution_aware_removal_strategy(self, default_attributions):
        """
        Build attribution-aware removal strategy for allotment clusters.

        Creates a removal strategy that prioritizes amendments with specific reviewer
        assignments over default attributions when selecting which amendments to keep
        in allotment clusters.

        Args:
            default_attributions: List of default attribution names to deprioritize

        Returns:
            Callable that takes (amendments_df, cluster) and returns list of amendment
            indices to remove from the cluster
        """

        def select_amendments_to_remove(
            amendments_df: pd.DataFrame, cluster: list[int]
        ):
            # Find amendments in cluster with non-default attributions
            affectation_series = amendments_df.loc[
                amendments_df["amdt_idx"].isin(cluster)
                & ~amendments_df["Affectation (nom)"].isin(default_attributions)
                & amendments_df["Affectation (nom)"].notna(),
                "Affectation (nom)",
            ]

            # If no specific attributions found, use default strategy (keep first)
            if affectation_series.empty:
                return cluster[1:]

            # Find the most common non-default attribution in this cluster
            value_counts = affectation_series.value_counts()
            if value_counts.empty:
                # No valid attributions found after value_counts (likely all NaN)
                return cluster[1:]

            most_common_affectation = value_counts.idxmax()

            # Get the first amendment with this most common attribution
            affectation_df = amendments_df.loc[
                (amendments_df["Affectation (nom)"] == most_common_affectation)
                & (amendments_df["amdt_idx"].isin(cluster)),
                "amdt_idx",
            ]
            if not affectation_df.empty:
                amdt_idx_with_most_common_affectation = affectation_df.iloc[0]
            else:
                amdt_idx_with_most_common_affectation = None

            # Remove all amendments except the one with most common attribution
            to_remove = [
                idx for idx in cluster if idx != amdt_idx_with_most_common_affectation
            ]
            return to_remove

        return select_amendments_to_remove
