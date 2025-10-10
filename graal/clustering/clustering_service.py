import logging
import logging.config
from typing import Dict, List, Optional, Tuple

import pandas as pd

from graal.clustering.cluster_finder import AmendmentsClusterFinder
from graal.custom_types import Acronym, IntIndex
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
        logging.debug(
            f"[CLUSTERING_PREPROCESSING] Starting preprocessing with {len(amendments_df)} amendments"
        )
        logging.debug(
            f"[CLUSTERING_PREPROCESSING] Columns to filter: {columns_to_filter}"
        )
        logging.debug(
            f"[CLUSTERING_PREPROCESSING] Columns to normalize: {columns_to_normalize}"
        )

        prepared_df = amendments_df.copy()

        # Clear columns if specified
        if columns_to_clear:
            logging.debug(
                f"[CLUSTERING_PREPROCESSING] Clearing columns: {columns_to_clear}"
            )
            prepared_df = AmendmentPreProcessor.clear_columns_to_be_overridden(
                amendments_df=prepared_df, columns_to_clear=columns_to_clear
            )

        # Apply acronym replacement if mapping is provided
        if acronym_mapping:
            logging.debug(
                f"[CLUSTERING_PREPROCESSING] Applying acronym mapping with {len(acronym_mapping)} entries"
            )
            prepared_df = AmendmentPreProcessor.replace_acronyms(
                amendments_df=prepared_df,
                acronym_mapping=acronym_mapping,
                columns_to_normalize=columns_to_normalize,
            )

        logging.debug(
            f"[CLUSTERING_PREPROCESSING] Before dropping empty rows: {len(prepared_df)} amendments"
        )
        prepared_df = AmendmentPreProcessor.drop_empty_rows_in_columns(
            amendments_df=prepared_df, columns_to_filter=columns_to_filter
        )
        logging.debug(
            f"[CLUSTERING_PREPROCESSING] After dropping empty rows: {len(prepared_df)} amendments"
        )

        prepared_df = AmendmentPreProcessor.handle_common_amendment_bodies(
            amendments_df=prepared_df
        )

        logging.debug("[CLUSTERING_PREPROCESSING] Before normalization - sample texts:")
        for col in columns_to_normalize:
            if col in prepared_df.columns:
                sample_texts = prepared_df[col].dropna().head(3)
                for idx, text in sample_texts.items():
                    logging.debug(f"[CLUSTERING_PREPROCESSING] {col}[{idx}]: '{text}'")

        prepared_df = AmendmentPreProcessor.normalize_amendments(
            amendments_df=prepared_df, columns_to_normalize=columns_to_normalize
        )

        logging.debug("[CLUSTERING_PREPROCESSING] After normalization - sample texts:")
        for col in columns_to_normalize:
            if col in prepared_df.columns:
                sample_texts = prepared_df[col].dropna().head(3)
                for idx, text in sample_texts.items():
                    logging.debug(f"[CLUSTERING_PREPROCESSING] {col}[{idx}]: '{text}'")

        logging.debug(
            f"[CLUSTERING_PREPROCESSING] Final preprocessing result: {len(prepared_df)} amendments"
        )
        return prepared_df

    @staticmethod
    def create_tfidf_clusters(
        normalized_amdt_df: pd.DataFrame,
        group_by_columns: List[str],
        text_column: str,
        eps: float = 0.4,
    ) -> Dict[Tuple, List[List[IntIndex]]]:
        """
        Create complete TF-IDF clusters ready for Levenshtein refinement.

        This performs COMPLETE TF-IDF clustering including:
        - Initial TF-IDF + DBSCAN clustering
        - Recursive subdivision of large clusters (>30 amendments)
        - Returns ONLY clusters ≤30 amendments (ready for O(n²) Levenshtein)

        Args:
            normalized_amdt_df: Preprocessed amendments dataframe
            group_by_columns: Columns to group by
            text_column: Column containing the text to analyze for similarity
            eps: Epsilon value for DBSCAN

        Returns:
            Dictionary of clusters, all with size ≤30 amendments
        """
        logging.info(
            f"Creating complete TF-IDF clusters of similar amendments on column {text_column}"
        )
        tfidf_clusters = AmendmentsClusterFinder.find_similarity_clusters(
            amendments_df=normalized_amdt_df,
            group_by_columns=group_by_columns,
            text_column=text_column,
            eps=eps,
        )
        return tfidf_clusters

    @staticmethod
    def apply_levenshtein_refinement(
        amendments_df: pd.DataFrame,
        group_by_columns: List[str],
        text_column: str,
        tfidf_clusters: Dict[Tuple, List[List[IntIndex]]],
        pct_threshold: float,
    ) -> Tuple[Dict[Tuple, List[List[IntIndex]]], Dict[int, Dict[int, float]]]:
        """
        Refine clusters using Damerau-Levenshtein distance.

        This phase:
        - Calculates precise edit distances between amendment pairs
        - Uses DBSCAN to refine clusters based on string similarity
        - Returns similarity percentages for downstream use

        Args:
            amendments_df: DataFrame containing amendments
            group_by_columns: Columns to group by when finding clusters
            text_column: Column containing the text to analyze for similarity
            tfidf_clusters: Complete TF-IDF clusters (all ≤30 amendments)
            pct_threshold: Similarity threshold as decimal (0.0-1.0)

        Returns:
            A tuple containing:
            - Dictionary of refined clusters
            - Dictionary of similarity percentages between amendments
        """
        logging.info("Refining clusters using Damerau-Levenshtein distance")

        # Convert similarity % threshold to distance threshold
        distance_threshold = 1.0 - pct_threshold

        refined_clusters, similarity_percentages = (
            AmendmentsClusterFinder.refine_with_levenshtein(
                amendments_df=amendments_df,
                group_by_columns=group_by_columns,
                text_column=text_column,
                tfidf_clusters=tfidf_clusters,
                distance_threshold=distance_threshold,
            )
        )
        return refined_clusters, similarity_percentages

    @staticmethod
    def get_clusters(
        normalized_amdt_df: pd.DataFrame,
        group_by_columns: List[str],
        text_column: str,
        eps: float = 0.4,
        refinement_pct_threshold: float = 0.9999,
    ) -> Tuple[Dict[Tuple, List[List[IntIndex]]], Dict[int, Dict[int, float]]]:
        """
        Get clusters of similar amendments (combined TF-IDF and refinement)

        Args:
            normalized_amdt_df: Preprocessed amendments dataframe
            group_by_columns: Columns to group by
            text_column: Column containing the text to analyze for similarity
            eps: Epsilon value for DBSCAN (range: 0.0 to 1.0)
            refinement_pct_threshold: Threshold for Levenshtein refinement as decimal percentage (range: 0.0 to 1.0)

        Returns:
            A tuple containing:
            - Dictionary of clusters
            - Dictionary of similarity percentages between amendments

        Raises:
            ValueError: If thresholds are outside valid range [0.0, 1.0]
        """
        # Validate threshold parameters
        if not 0.0 <= eps <= 1.0:
            raise ValueError(f"eps must be between 0.0 and 1.0, got {eps}")
        if not 0.0 <= refinement_pct_threshold <= 1.0:
            raise ValueError(
                f"refinement_pct_threshold must be between 0.0 and 1.0, got {refinement_pct_threshold}"
            )
        logging.info(f"Get clusters of similar amendments using column {text_column}")
        tfidf_clusters = ClusteringService.create_tfidf_clusters(
            normalized_amdt_df=normalized_amdt_df,
            group_by_columns=group_by_columns,
            text_column=text_column,
            eps=eps,
        )
        clusters, similarity_percentages = (
            ClusteringService.apply_levenshtein_refinement(
                amendments_df=normalized_amdt_df,
                group_by_columns=group_by_columns,
                text_column=text_column,
                tfidf_clusters=tfidf_clusters,
                pct_threshold=refinement_pct_threshold,
            )
        )
        return clusters, similarity_percentages
