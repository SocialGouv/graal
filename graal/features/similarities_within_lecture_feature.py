"""
Similarities within lectures feature implementation.

This feature finds similarities between amendments within the same document.
"""

from typing import Any, Set

import pandas as pd

from graal.core.feature_interface import BaseFeature, FeatureInput, FeatureOutput
from graal.similarities.within_lecture_similarity_handler import (
    WithinLectureSimilarityHandler,
)


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

        # Find similarities (keep amdt_idx as column for clustering pipeline)
        similarity_results = WithinLectureSimilarityHandler.find_similar_amendments(
            amendments_df=working_df,
            similarities_column=similarities_column,
            pct_similarity_threshold=similarity_threshold,
            group_by_columns=["Num article"],
            eps=tf_idf_threshold,
        )

        # Set index before applying comments (required by apply_similarity_comments)
        working_df_indexed = working_df.set_index("amdt_idx")

        # Apply similarity comments using the handler's method
        result_df = WithinLectureSimilarityHandler.apply_similarity_comments(
            amendments_df=working_df_indexed,
            similarity_results=similarity_results,
        )

        # Reset index to match original format
        result_df = result_df.reset_index()

        # Create final result
        final_df = feature_input.amendments_df.copy()
        if "Commentaires" not in final_df.columns:
            final_df["Commentaires"] = pd.NA

        # Update the Commentaires column if we have results
        if len(similarity_results) > 0 and "Commentaires" in result_df.columns:
            # Merge the comments back to the original dataframe using amdt_idx
            comments_map = result_df.set_index("amdt_idx")["Commentaires"]

            # Map using amdt_idx column instead of index
            mapped_comments = final_df["amdt_idx"].map(comments_map)

            # Fill nulls with existing Commentaires values
            final_df["Commentaires"] = mapped_comments.fillna(final_df["Commentaires"])

        return FeatureOutput(
            amendments_df=final_df,
            outputs={
                "processed_amendments": len(
                    [idx for idx in similarity_results if idx in working_df.index]
                ),
                "similarities_found": len(similarity_results),
                "similarity_threshold": similarity_threshold,
            },
        )
