"""
Similarities within lectures feature implementation.

This feature finds similarities between amendments within the same document.
"""

from typing import Any, Set

import pandas as pd

from graal.core.feature_interface import BaseFeature, FeatureInput, FeatureOutput


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
        from graal.similarities.similarities_handler import SimilaritiesHandler

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
        similarity_results = SimilaritiesHandler.find_similar_amendments(
            amendments_df=working_df,
            similarities_column=similarities_column,
            pct_similarity_threshold=similarity_threshold,
            group_by_columns=["Num article"],
            eps=tf_idf_threshold,
        )

        # Build a DataFrame with only the rows that have similarity results
        # This ensures we don't overwrite existing comments with empty values
        result_rows = []

        if similarity_results:
            for amdt_idx, similar_amdts in similarity_results.items():
                # Skip if the amendment is not in our dataframe
                amdt_mask = working_df["amdt_idx"] == amdt_idx
                if not amdt_mask.any():
                    continue

                # Get the row for this amendment
                row = working_df[amdt_mask].iloc[0].copy()

                # Format the comment
                similarity_comment = SimilaritiesHandler.format_similarity_comment(
                    similar_amdts
                )

                # Set the comment for this row
                row["Commentaires"] = similarity_comment
                result_rows.append(row)

        # Create result_df with only rows that have similarities
        if result_rows:
            result_df = pd.DataFrame(result_rows)
            result_df.set_index("amdt_idx", inplace=True)
        else:
            # No similarities found, return empty result
            result_df = pd.DataFrame(columns=["amdt_idx", "Commentaires"]).set_index(
                "amdt_idx"
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
