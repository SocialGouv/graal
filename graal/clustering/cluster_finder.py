import logging

import numpy as np
import pandas as pd
from rapidfuzz.distance import DamerauLevenshtein
from sklearn.cluster import DBSCAN
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from graal.custom_types import IntIndex


class AmendmentsClusterFinder:
    """Find clusters of similar amendments using DBSCAN on TF-IDF vectors"""

    @staticmethod
    def find_similarity_clusters(  # noqa: C901
        amendments_df: pd.DataFrame,
        group_by_columns: list[str],
        text_column: str = "Corps amdt",
        eps: float = 0.5,
        min_samples: int = 2,
    ) -> dict[tuple, list[list[IntIndex]]]:
        """Find clusters using DBSCAN on the cosine similarity matrix"""
        # Vectorize all data
        logging.info(
            f"Converting strings to TF-IDF vectors for all data from column {text_column}...\n"
        )
        strings = amendments_df[text_column].tolist()

        # Debug logging for TF-IDF input
        logging.debug(f"[TF_IDF_CLUSTERING] Total number of strings: {len(strings)}")
        for i, string in enumerate(strings[:10]):  # Log first 10 strings
            logging.debug(f"[TF_IDF_CLUSTERING] String {i}: '{string}'")
        if len(strings) > 10:
            logging.debug(
                f"[TF_IDF_CLUSTERING] ... and {len(strings) - 10} more strings"
            )

        # Check for empty strings
        empty_strings = [i for i, s in enumerate(strings) if not s or not s.strip()]
        if empty_strings:
            logging.warning(
                f"[TF_IDF_CLUSTERING] Found {len(empty_strings)} empty strings at indices: {empty_strings[:10]}"
            )

        # Safety check: ensure we have valid strings for TF-IDF
        valid_strings = [s for s in strings if s and s.strip()]
        if not valid_strings:
            error_msg = (
                f"[TF_IDF_CLUSTERING] No valid strings found for TF-IDF clustering! "
                f"All {len(strings)} strings are empty or whitespace-only. "
                f"This suggests that text preprocessing removed all content from the '{text_column}' column. "
                f"Check the text normalization pipeline, especially stop word removal."
            )
            logging.error(error_msg)
            raise ValueError(
                "No valid strings for TF-IDF clustering - all text was filtered out during preprocessing"
            )

        if len(valid_strings) != len(strings):
            logging.warning(
                f"[TF_IDF_CLUSTERING] Only {len(valid_strings)}/{len(strings)} strings are valid for TF-IDF"
            )

        vectorizer = TfidfVectorizer()
        try:
            vectorizer.fit(strings)
            logging.debug(
                f"[TF_IDF_CLUSTERING] TF-IDF vectorizer fitted successfully. Vocabulary size: {len(vectorizer.vocabulary_)}"
            )
        except ValueError as e:
            logging.error(f"[TF_IDF_CLUSTERING] TF-IDF vectorizer failed to fit: {e}")
            logging.error(f"[TF_IDF_CLUSTERING] All strings being processed: {strings}")
            logging.error(f"[TF_IDF_CLUSTERING] Valid strings: {valid_strings}")
            logging.error(
                "[TF_IDF_CLUSTERING] This likely means text preprocessing was too aggressive and removed all meaningful content"
            )
            raise

        tfidf_clusters_per_group: dict[tuple, list[list[IntIndex]]] = {}
        group_keys = (
            amendments_df[group_by_columns]
            .drop_duplicates()
            .itertuples(index=False, name=None)
        )

        logging.debug(
            f"[TF_IDF_CLUSTERING] Found {len(list(group_keys))} unique groups"
        )
        group_keys = list(group_keys)  # Convert back to list since we consumed it above

        for i, group_key in enumerate(group_keys):
            logging.debug(
                f"[TF_IDF_CLUSTERING] Processing group {i + 1}/{len(group_keys)}: {group_key}"
            )

            # Transform group
            df_group = amendments_df[
                (
                    amendments_df[group_by_columns]
                    == pd.Series(group_key, index=group_by_columns)
                ).all(axis=1)
            ]

            logging.debug(
                f"[TF_IDF_CLUSTERING] Group {group_key} has {len(df_group)} amendments"
            )

            if len(df_group) == 0:
                logging.warning(
                    f"[TF_IDF_CLUSTERING] Group {group_key} is empty, skipping"
                )
                continue

            group_strings = df_group[text_column].tolist()
            logging.debug(
                f"[TF_IDF_CLUSTERING] Group {group_key} strings: {group_strings[:3]}{'...' if len(group_strings) > 3 else ''}"
            )

            if not group_strings or all(not s or not s.strip() for s in group_strings):
                logging.warning(
                    f"[TF_IDF_CLUSTERING] Group {group_key} has no valid strings, skipping"
                )
                continue

            vectors = vectorizer.transform(group_strings)
            logging.debug(
                f"[TF_IDF_CLUSTERING] Group {group_key} vectorized to shape: {vectors.shape}"
            )

            # Compute distance matrix
            similarity_matrix = cosine_similarity(vectors)
            distance_matrix = 1 - similarity_matrix
            distance_matrix[distance_matrix < 0] = 0  # Ensure no negative values

            # Apply DBSCAN
            dbscan = DBSCAN(metric="precomputed", eps=eps, min_samples=min_samples)
            clusters = dbscan.fit_predict(distance_matrix)

            # Extract clusters
            clustered_strings: dict[int, list[IntIndex]] = {}
            amdt_idx_list = df_group["amdt_idx"].tolist()

            for idx, label in enumerate(clusters):
                if label == -1:  # Ignore noise points
                    continue
                if label not in clustered_strings:
                    clustered_strings[label] = []
                clustered_strings[label].append(amdt_idx_list[idx])

            # Filter out singleton clusters
            tfidf_clusters_per_group[group_key] = [
                cluster for cluster in clustered_strings.values() if len(cluster) > 1
            ]

        return tfidf_clusters_per_group

    @staticmethod
    def _process_cluster_static(
        df_group: pd.DataFrame,
        cluster: list[IntIndex],
        similarity_percentages: dict[int, dict[int, float]],
        distance_threshold: float,
        text_column: str,
    ) -> list[list[IntIndex]]:
        """
        Process a single cluster to find refined clusters (static version)

        Args:
            df_group: Dataframe filtered by group key
            cluster: List of amendment indices in the cluster
            similarity_percentages: Dictionary to store similarity percentages (modified in place)
            distance_threshold: Threshold for DBSCAN clustering
            text_column: Column containing the text to analyze for similarity

        Returns:
            List of refined clusters
        """
        # Get the strings and corresponding amdt_idx for the current cluster
        strings = df_group[df_group["amdt_idx"].isin(cluster)][text_column].tolist()
        cluster_amdt_idx = df_group[df_group["amdt_idx"].isin(cluster)][
            "amdt_idx"
        ].tolist()

        # Handle empty clusters (no matching amendments in this group)
        if len(strings) == 0:
            return []

        # Calculate distance matrix and similarity percentages
        n = len(strings)
        damerau_distance_matrix = np.zeros((n, n))

        # Calculate distances and store similarity percentages
        for i in range(n):
            amdt_i = cluster_amdt_idx[i]
            if amdt_i not in similarity_percentages:
                similarity_percentages[amdt_i] = {}

            for j in range(n):
                if i == j:
                    continue

                amdt_j = cluster_amdt_idx[j]
                distance = DamerauLevenshtein.distance(strings[i], strings[j])
                normalized_distance = distance / max(len(strings[i]), len(strings[j]))

                # Store similarity percentage
                similarity_percentage = (1 - normalized_distance) * 100
                similarity_percentages[amdt_i][amdt_j] = similarity_percentage

                # Only need to fill the distance matrix for i < j
                if i < j:
                    damerau_distance_matrix[i][j] = normalized_distance
                    damerau_distance_matrix[j][i] = normalized_distance

        # Apply DBSCAN on the refined distance matrix
        dbscan = DBSCAN(metric="precomputed", eps=distance_threshold, min_samples=2)
        refined_cluster_labels = dbscan.fit_predict(damerau_distance_matrix)

        # Extract refined clusters
        refined_clustered_strings: dict[int, list[IntIndex]] = {}
        for idx, label in enumerate(refined_cluster_labels):
            if label == -1:  # Ignore noise points
                continue
            if label not in refined_clustered_strings:
                refined_clustered_strings[label] = []
            refined_clustered_strings[label].append(cluster_amdt_idx[idx])

        # Filter out singleton clusters
        refined_clusters = [
            refined_cluster
            for refined_cluster in refined_clustered_strings.values()
            if len(refined_cluster) > 1
        ]

        return refined_clusters

    @staticmethod
    def refine_clusters_with_distance(
        amendments_df: pd.DataFrame,
        group_by_columns: list[str],
        text_column: str,
        tfidf_clusters: dict[tuple, list[list[int]]],
        distance_threshold: float,
    ) -> tuple[dict[tuple, list[list[int]]], dict[int, dict[int, float]]]:
        """
        Refine clusters using Damerau-Levenshtein distance

        Args:
            amendments_df: DataFrame containing amendments
            group_by_columns: Columns to group by when finding clusters
            text_column: Column containing the text to analyze for similarity
            tfidf_clusters: Initial clusters from TF-IDF clustering
            distance_threshold: Threshold for DBSCAN clustering

        Returns:
            A tuple containing:
            - Dictionary of refined clusters
            - Dictionary of similarity percentages between amendments
        """
        group_keys = (
            amendments_df[group_by_columns]
            .drop_duplicates()
            .itertuples(index=False, name=None)
        )
        similarity_percentages: dict[int, dict[int, float]] = {}
        final_clusters_per_group: dict[tuple, list[list[IntIndex]]] = {}

        for group_key in group_keys:
            # Get dataframe filtered by group key
            df_group = amendments_df[
                (
                    amendments_df[group_by_columns]
                    == pd.Series(group_key, index=group_by_columns)
                ).all(axis=1)
            ]
            refined_clusters = []

            for cluster in tfidf_clusters.get(group_key, []):
                cluster_refined = AmendmentsClusterFinder._process_cluster_static(
                    df_group,
                    cluster,
                    similarity_percentages,
                    distance_threshold,
                    text_column,
                )
                refined_clusters.extend(cluster_refined)

            final_clusters_per_group[group_key] = refined_clusters

        return final_clusters_per_group, similarity_percentages
