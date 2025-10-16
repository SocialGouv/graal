"""
Similarities within lectures feature implementation.

This feature finds similarities between amendments within the same document.
"""

from typing import Any, Set

import pandas as pd

from graal.core.feature_interface import BaseFeature, FeatureInput, FeatureOutput
from graal.similarities.similarity_search_handler import SimilaritySearchHandler


class SimilaritiesWithinLecturesFeature(BaseFeature):
    """
    Finds similarities within the same document.
    """

    def __init__(self, config: dict[str, Any] = None):
        super().__init__("similarities_within_lectures")
        self.config = config or {}

    def get_required_columns(self) -> Set[str]:
        """Similarities within lectures requires these columns."""
        similarities_column = "Exposé amdt"  # Default
        if self.config:
            similarities_column = self.config.get(
                "similarities_within_lectures", {}
            ).get("column", "Exposé amdt")

        return {
            similarities_column,
            "amdt_idx",
            "Num article",
        }

    def get_output_columns(self) -> Set[str]:
        """Similarities within lectures updates comments."""
        return {"Commentaires"}

    def is_enabled(self, config: dict[str, Any]) -> bool:
        """Check if similarities within lectures is enabled."""
        return config.get("similarities_within_lectures", {}).get("enabled", False)

    def get_columns_to_clear(self, config: dict[str, Any]) -> Set[str]:
        """This feature doesn't clear any columns, it only appends to Commentaires."""
        return set()

    def process(self, feature_input: FeatureInput) -> FeatureOutput:
        """
        Process amendments for similarities within lectures.
        """

        # Work with our own copy
        working_df = feature_input.amendments_df.copy()
        similarities_config = feature_input.config.get(
            "similarities_within_lectures", {}
        )

        # Get configuration
        similarities_column = similarities_config.get("column", "Exposé amdt")
        similarity_threshold = similarities_config.get("similarity_threshold", 0.8)
        tf_idf_threshold = feature_input.config.get("similarity_thresholds", {}).get(
            "tf_idf_threshold", 0.4
        )

        # Find similarities
        similarity_results = SimilaritySearchHandler.find_similar_amendments(
            amendments_df=working_df,
            similarities_column=similarities_column,
            pct_similarity_threshold=similarity_threshold,
            group_by_columns=["Num article"],
            eps=tf_idf_threshold,
        )

        # Apply similarity comments using the handler's method
        result_df = SimilaritySearchHandler.apply_similarity_comments(
            amendments_df=working_df,
            similarity_results=similarity_results,
        )

        # Create final result using declared output columns
        output_columns = self.get_output_columns()
        final_df = feature_input.amendments_df.copy()

        # Only include output columns if we have actual results to report
        # Don't create empty columns that would interfere with concatenation from other features
        if len(result_df) > 0:
            for col in output_columns:
                if col in result_df.columns:
                    # Initialize column with pd.NA for all rows
                    if col not in final_df.columns:
                        final_df[col] = pd.NA
                    # Then update only the rows with similarity results
                    final_df.loc[result_df.index, col] = result_df[col]

        return FeatureOutput(
            amendments_df=final_df,
            outputs={
                "processed_amendments": len(result_df),
                "similarities_found": len(similarity_results)
                if similarity_results
                else 0,
                "similarity_threshold": similarity_threshold,
            },
        )
