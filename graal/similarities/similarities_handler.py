import logging
import logging.config
from typing import Dict, List, Optional

import pandas as pd

from graal.clustering.clustering_service import ClusteringService

logging.config.fileConfig("logging.conf")


class SimilaritiesHandler:
    """Handler for finding and processing similarities between amendments."""

    @staticmethod
    def update_comments_with_similarities(
        amendments_df: pd.DataFrame,
        similarity_percentages: Dict[int, Dict[int, float]],
    ) -> pd.DataFrame:
        """
        Update the 'Commentaires' column with similarity information.

        For each amendment, adds a line in the 'Commentaires' column listing
        all similar amendments with their similarity percentages that meet
        the specified threshold.

        Args:
            amendments_df: The dataframe containing the amendments
            similarity_percentages: Dictionary mapping amendment indices to
                                    dictionaries of similar amendment indices
                                    with their similarity percentages
            pct_threshold: The similarity threshold as a percentage (0.0 to 1.0)
                       where 1.0 means 100% similar
        """
        logging.info("Updating comments with similarity information")
        result_df = amendments_df.copy()

        for amdt_idx, similarities in similarity_percentages.items():
            if not similarities:
                continue

            # Get the amendment number for the current amendment
            current_amdt_row = result_df[result_df["amdt_idx"] == amdt_idx]
            if current_amdt_row.empty:
                continue
            current_num = current_amdt_row["Num amdt"].iloc[0]

            # Get the amendment numbers for the similar amendments that meet the threshold
            similar_amdts = []
            for similar_idx, percentage in similarities.items():
                similar_amdt_row = result_df[result_df["amdt_idx"] == similar_idx]
                if not similar_amdt_row.empty:
                    similar_num = similar_amdt_row["Num amdt"].iloc[0]
                    if similar_num != current_num:
                        similar_amdts.append(f"{similar_num} ({percentage:.0f}%)")

            if similar_amdts:
                # Format the comment
                similarity_comment = f"Amdt similaires : {', '.join(similar_amdts)}"

                # Update the 'Commentaires' column
                current_comment = current_amdt_row["Commentaires"].iloc[0]
                if pd.isna(current_comment) or current_comment == "":
                    new_comment = similarity_comment
                else:
                    new_comment = f"{current_comment}\n{similarity_comment}"

                result_df.loc[result_df["amdt_idx"] == amdt_idx, "Commentaires"] = (
                    new_comment
                )

        return result_df

    @staticmethod
    def process_similarities(
        amendments_df: pd.DataFrame,
        similarities_column: str,
        pct_similarity_threshold: float = 0.8,
        group_by_columns: Optional[List[str]] = None,
        eps: float = 0.4,
    ) -> pd.DataFrame:
        """
        Process similarities in a single method that orchestrates the entire workflow

        Args:
            amendments_df: The dataframe containing amendments
            similarities_column: The column to use for similarity calculation and text analysis
            pct_similarity_threshold: Threshold for similarity (0.0 to 1.0)
            group_by_columns: Columns to group by
            eps: Epsilon value for DBSCAN

        Returns:
            The dataframe with updated comments containing similarity information
        """
        # Preprocess amendments
        if group_by_columns is None:
            group_by_columns = ["Num article"]
        normalized_df = ClusteringService.preprocess_amendments(
            amendments_df=amendments_df,
            columns_to_filter=[similarities_column],
            columns_to_normalize=[similarities_column],
        )

        # Get clusters and similarity percentages
        similar_amdt_clusters, similarity_percentages = ClusteringService.get_clusters(
            normalized_amdt_df=normalized_df,
            group_by_columns=group_by_columns,
            text_column=similarities_column,
            eps=eps,
            refinement_pct_threshold=pct_similarity_threshold,
        )

        # Log similarity percentages
        logging.warning(f"similarity_percentages {similarity_percentages}")

        # Update comments
        result_df = SimilaritiesHandler.update_comments_with_similarities(
            amendments_df=amendments_df,
            similarity_percentages=similarity_percentages,
        )

        return result_df
