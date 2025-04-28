import logging
import logging.config
from typing import List, Optional

import pandas as pd

from graal.clustering.clustering_service import ClusteringService
from graal.custom_types import SimilarAmendment, SimilarityResult

logging.config.fileConfig("logging.conf")


class SimilaritiesHandler:
    """Handler for finding and processing similarities between amendments."""

    @staticmethod
    def format_similarity_comment(similar_amendments: List[SimilarAmendment]) -> str:
        """
        Format a list of similar amendments into a comment string

        Args:
            similar_amendments: List of SimilarAmendment objects

        Returns:
            Formatted comment string
        """
        formatted_amdts = [
            f"{amdt['amdt_num']} ({amdt['similarity_percentage']:.0f}%)"
            for amdt in similar_amendments
        ]
        return f"Amdt similaires : {', '.join(formatted_amdts)}"

    @staticmethod
    def find_similar_amendments(
        amendments_df: pd.DataFrame,
        similarities_column: str,
        pct_similarity_threshold: float = 0.8,
        group_by_columns: Optional[List[str]] = None,
        eps: float = 0.4,
    ) -> SimilarityResult:
        """
        Find similar amendments and return a dictionary mapping amendment indices
        to lists of similar amendments with similarity percentages.

        Args:
            amendments_df: The dataframe containing amendments
            similarities_column: The column to use for similarity calculation
            pct_similarity_threshold: Threshold for similarity (0.0 to 1.0)
            group_by_columns: Columns to group by (default: ["Num article"])
            eps: Epsilon value for DBSCAN clustering

        Returns:
            A dictionary mapping amendment indices to lists of similar amendments
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
        _, similarity_percentages = ClusteringService.get_clusters(
            normalized_amdt_df=normalized_df,
            group_by_columns=group_by_columns,
            text_column=similarities_column,
            eps=eps,
            refinement_pct_threshold=pct_similarity_threshold,
        )

        # Convert to the desired return format
        result: SimilarityResult = {}

        # Create a mapping from amdt_idx to Num amdt for quick lookups
        idx_to_num = dict(
            zip(amendments_df["amdt_idx"], amendments_df["Num amdt"], strict=False)
        )

        for amdt_idx, similarities in similarity_percentages.items():
            if not similarities:
                continue

            similar_amdts: list[SimilarAmendment] = []
            current_num = idx_to_num.get(amdt_idx)

            for similar_idx, percentage in similarities.items():
                similar_num = idx_to_num.get(similar_idx)
                if similar_num is not None and similar_num != current_num:
                    similar_amdts.append(
                        {"amdt_num": similar_num, "similarity_percentage": percentage}
                    )

            if similar_amdts:
                result[amdt_idx] = similar_amdts

        return result
