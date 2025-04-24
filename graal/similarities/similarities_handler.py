import logging
import logging.config
from typing import Dict, List, Optional, Tuple

import pandas as pd
from rapidfuzz.distance import DamerauLevenshtein

from graal.clustering.clustering_service import ClusteringService
from graal.custom_types import IntIndex

logging.config.fileConfig("logging.conf")


class SimilaritiesHandler:
    """Handler for finding and processing similarities between amendments."""

    @staticmethod
    def calculate_similarity_percentages(
        normalized_amdt_df: pd.DataFrame,
        similar_amdt_clusters: Dict[Tuple, List[List[IntIndex]]],
    ) -> Dict[int, Dict[int, float]]:
        """
        Calculate similarity percentages between amendments in each cluster.

        Returns a dictionary mapping each amendment index to a dictionary of
        similar amendment indices with their similarity percentages.
        """
        logging.info("Calculating similarity percentages between amendments...")
        similarity_percentages: dict[int, dict[int, float]] = {}

        for clusters in similar_amdt_clusters.values():
            for cluster in clusters:
                # Get the strings for the current cluster
                cluster_df = normalized_amdt_df[
                    normalized_amdt_df["amdt_idx"].isin(cluster)
                ]
                strings = cluster_df["Corps amdt"].tolist()
                amdt_indices = cluster_df["amdt_idx"].tolist()

                n = len(strings)

                # Calculate Damerau-Levenshtein distances
                for i in range(n):
                    if amdt_indices[i] not in similarity_percentages:
                        similarity_percentages[amdt_indices[i]] = {}

                    for j in range(n):
                        if i == j:
                            continue

                        distance = DamerauLevenshtein.distance(strings[i], strings[j])
                        normalized_distance = distance / max(
                            len(strings[i]), len(strings[j])
                        )
                        similarity_percentage = (1 - normalized_distance) * 100

                        similarity_percentages[amdt_indices[i]][amdt_indices[j]] = (
                            similarity_percentage
                        )

        return similarity_percentages

    @staticmethod
    def update_comments_with_similarities(
        amendments_df: pd.DataFrame,
        similarity_percentages: Dict[int, Dict[int, float]],
        threshold: float = 0.8,
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
            threshold: The similarity threshold as a percentage (0.0 to 1.0)
                       where 1.0 means 100% similar
        """
        logging.info("Updating comments with similarity information")
        result_df = amendments_df.copy()
        threshold_percentage = threshold * 100  # Convert to percentage

        for amdt_idx, similarities in similarity_percentages.items():
            if not similarities:
                continue

            # Get the amendment number for the current amendment
            current_amdt_row = result_df[result_df["amdt_idx"] == amdt_idx]
            if current_amdt_row.empty:
                continue

            # Get the amendment numbers for the similar amendments that meet the threshold
            similar_amdts = []
            for similar_idx, percentage in similarities.items():
                # Only include amendments that meet the threshold
                if percentage < threshold_percentage:
                    continue

                similar_amdt_row = result_df[result_df["amdt_idx"] == similar_idx]
                if not similar_amdt_row.empty:
                    similar_num = similar_amdt_row["Num amdt"].iloc[0]
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
        similarity_threshold: float = 0.8,
        group_by_columns: Optional[List[str]] = None,
        eps: float = 0.4,
    ) -> Tuple[pd.DataFrame, Dict[Tuple, List[List[IntIndex]]]]:
        """
        Process similarities in a single method that orchestrates the entire workflow

        Args:
            amendments_df: The dataframe containing amendments
            similarities_column: The column to use for similarity calculation
            similarity_threshold: Threshold for similarity (0.0 to 1.0)
            group_by_columns: Columns to group by
            eps: Epsilon value for DBSCAN

        Returns:
            Tuple containing:
            - The dataframe with updated comments
            - The clusters of similar amendments
        """
        # Preprocess amendments
        if group_by_columns is None:
            group_by_columns = ["Num article"]
        normalized_df = ClusteringService.preprocess_amendments(
            amendments_df=amendments_df,
            columns_to_filter=[similarities_column],
            columns_to_normalize=[similarities_column],
        )

        # Get clusters
        similar_amdt_clusters = ClusteringService.get_clusters(
            normalized_amdt_df=normalized_df,
            group_by_columns=group_by_columns,
            eps=eps,
            threshold=similarity_threshold,
            is_similarity_threshold=True,
        )

        # Calculate similarity percentages
        similarity_percentages = SimilaritiesHandler.calculate_similarity_percentages(
            normalized_amdt_df=normalized_df,
            similar_amdt_clusters=similar_amdt_clusters,
        )

        # Update comments
        result_df = SimilaritiesHandler.update_comments_with_similarities(
            amendments_df=amendments_df,
            similarity_percentages=similarity_percentages,
            threshold=similarity_threshold,
        )

        return result_df, similar_amdt_clusters
