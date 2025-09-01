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
    def find_similarity_clusters(
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
        vectorizer = TfidfVectorizer()
        vectorizer.fit(strings)

        tfidf_clusters_per_group: dict[tuple, list[list[IntIndex]]] = {}
        group_keys = (
            amendments_df[group_by_columns]
            .drop_duplicates()
            .itertuples(index=False, name=None)
        )

        for group_key in group_keys:
            # Transform group
            df_group = amendments_df[
                (
                    amendments_df[group_by_columns]
                    == pd.Series(group_key, index=group_by_columns)
                ).all(axis=1)
            ]
            group_strings = df_group[text_column].tolist()
            vectors = vectorizer.transform(group_strings)

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
