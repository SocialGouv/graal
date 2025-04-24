import logging
import logging.config
from typing import Dict, List, Tuple, Optional

import pandas as pd

from graal.clustering.cluster_finder import AmendmentsClusterFinder
from graal.custom_types import IntIndex, Acronym
from graal.utils.amendment_pre_processor import AmendmentPreProcessor

logging.config.fileConfig("logging.conf")


class ClusteringService:
    """Service for clustering amendments based on similarity."""

    @staticmethod
    def preprocess_amendments(
        amendments_df: pd.DataFrame,
        columns_to_filter: List[str],
        columns_to_normalize: List[str],
        acronym_mapping: Optional[Dict[Acronym, str]] = None,
        columns_to_clear: Optional[List[str]] = None,
    ) -> pd.DataFrame:
        """Preprocess amendments for clustering."""
        prepared_df = amendments_df.copy()

        # Clear columns if specified
        if columns_to_clear:
            prepared_df = AmendmentPreProcessor.clear_columns_to_be_overridden(
                amendments_df=prepared_df, columns_to_clear=columns_to_clear
            )

        # Apply acronym replacement if mapping is provided
        if acronym_mapping:
            prepared_df = AmendmentPreProcessor.replace_acronyms(
                amendments_df=prepared_df,
                acronym_mapping=acronym_mapping,
                columns_to_normalize=columns_to_normalize,
            )

        prepared_df = AmendmentPreProcessor.drop_empty_rows_in_columns(
            amendments_df=prepared_df, columns_to_filter=columns_to_filter
        )
        prepared_df = AmendmentPreProcessor.handle_common_amendment_bodies(
            amendments_df=prepared_df
        )
        prepared_df = AmendmentPreProcessor.normalize_amendments(
            amendments_df=prepared_df, columns_to_normalize=columns_to_normalize
        )

        return prepared_df

    @staticmethod
    def create_tfidf_clusters(
        normalized_amdt_df: pd.DataFrame,
        group_by_columns: List[str],
        eps: float = 0.4,
    ) -> Tuple[AmendmentsClusterFinder, Dict[Tuple, List[List[IntIndex]]]]:
        """Create initial clusters using TF-IDF and DBSCAN"""
        logging.info("Creating initial clusters of similar amendments using TF-IDF")
        cluster_finder = AmendmentsClusterFinder(
            amendments_df=normalized_amdt_df, group_by_columns=group_by_columns
        )
        tfidf_clusters = cluster_finder.find_similarity_clusters(eps=eps)
        return cluster_finder, tfidf_clusters

    @staticmethod
    def apply_levenshtein_refinement(
        cluster_finder: AmendmentsClusterFinder,
        threshold: float,
        is_similarity_threshold: bool = False,
    ) -> Dict[Tuple, List[List[IntIndex]]]:
        """
        Refine clusters using Damerau-Levenshtein distance

        Args:
            cluster_finder: The cluster finder instance
            threshold: The threshold value
            is_similarity_threshold: If True, threshold is a similarity percentage (0.0 to 1.0)
                                    If False, threshold is a distance value
        """
        logging.info("Refining clusters using Damerau-Levenshtein distance")

        # Convert similarity threshold to distance threshold if needed
        distance_threshold = threshold
        if is_similarity_threshold:
            distance_threshold = 1.0 - threshold

        refined_clusters = cluster_finder.refine_clusters_with_distance(
            threshold=distance_threshold
        )
        return refined_clusters

    @staticmethod
    def get_clusters(
        normalized_amdt_df: pd.DataFrame,
        group_by_columns: List[str],
        eps: float = 0.4,
        threshold: float = 0.0001,
        is_similarity_threshold: bool = False,
    ) -> Dict[Tuple, List[List[IntIndex]]]:
        """
        Get clusters of similar amendments (combined TF-IDF and refinement)

        Args:
            normalized_amdt_df: Preprocessed amendments dataframe
            group_by_columns: Columns to group by
            eps: Epsilon value for DBSCAN
            threshold: Threshold for Levenshtein refinement
            is_similarity_threshold: Whether threshold is a similarity percentage
        """
        logging.info("Get clusters of similar amendments")
        cluster_finder, _ = ClusteringService.create_tfidf_clusters(
            normalized_amdt_df=normalized_amdt_df,
            group_by_columns=group_by_columns,
            eps=eps,
        )
        return ClusteringService.apply_levenshtein_refinement(
            cluster_finder=cluster_finder,
            threshold=threshold,
            is_similarity_threshold=is_similarity_threshold,
        )
