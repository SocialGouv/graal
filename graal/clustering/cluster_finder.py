import logging

import numpy as np
import pandas as pd
from numpy import ndarray
from rapidfuzz.distance import DamerauLevenshtein
from scipy.sparse import spmatrix
from sklearn.cluster import DBSCAN
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from graal.custom_types import IntIndex


class AmendmentsClusterFinder:
    """Find clusters of similar amendments using DBSCAN on TF-IDF vectors"""

    def __init__(
        self,
        amendments_df: pd.DataFrame,
        group_by_columns: list[str],
        text_column: str = "Corps amdt",
    ):
        """
        Initialize the AmendmentsClusterFinder.

        Args:
            amendments_df: DataFrame containing amendments
            group_by_columns: Columns to group by when finding clusters
            text_column: Column containing the text to analyze for similarity (default: "Corps amdt")
        """
        self.amendments_df = amendments_df.copy()
        self.group_by_columns = group_by_columns
        self.text_column = text_column
        self.vectorizer = TfidfVectorizer()
        self.vectors_per_group: dict[tuple, spmatrix] = {}
        self.distance_matrix_per_group: dict[tuple, ndarray] = {}
        self.tfidf_clusters_per_group: dict[tuple, list[list[IntIndex]]] = {}
        self.final_clusters_per_group: dict[tuple, list[list[IntIndex]]] = {}

    def _vectorize_data(self) -> None:
        """Convert strings to TF-IDF vectors for all text data"""
        logging.info(
            f"Converting strings to TF-IDF vectors for all data from column {self.text_column}...\n"
        )
        strings = self.amendments_df[self.text_column].tolist()
        self.vectorizer.fit(strings)

    def _transform_group(self, group_key: tuple) -> None:
        """Transform strings to TF-IDF vectors for a specific group"""
        df_group = self.amendments_df[
            (
                self.amendments_df[self.group_by_columns]
                == pd.Series(group_key, index=self.group_by_columns)
            ).all(axis=1)
        ]
        strings = df_group[self.text_column].tolist()
        self.vectors_per_group[group_key] = self.vectorizer.transform(strings)

    def _compute_distance_matrix(self, group_key: tuple) -> None:
        """Compute cosine similarity matrix for a specific group"""
        similarity_matrix = cosine_similarity(self.vectors_per_group[group_key])
        distance_matrix = 1 - similarity_matrix
        distance_matrix[distance_matrix < 0] = 0  # Ensure no negative values
        self.distance_matrix_per_group[group_key] = distance_matrix

    # TODO: Refactor callers so this can be used as a static method.
    def find_similarity_clusters(
        self, eps: float = 0.5, min_samples: int = 2
    ) -> dict[tuple, list[list[int]]]:
        """Find clusters using DBSCAN on the cosine similarity matrix"""
        self._vectorize_data()
        group_keys = (
            self.amendments_df[self.group_by_columns]
            .drop_duplicates()
            .itertuples(index=False, name=None)
        )
        for group_key in group_keys:
            self._transform_group(group_key)
            self._compute_distance_matrix(group_key)
            dbscan = DBSCAN(metric="precomputed", eps=eps, min_samples=min_samples)
            clusters = dbscan.fit_predict(self.distance_matrix_per_group[group_key])

            # Extract clusters
            clustered_strings: dict[int, list[IntIndex]] = {}
            df_group = self.amendments_df[
                (
                    self.amendments_df[self.group_by_columns]
                    == pd.Series(group_key, index=self.group_by_columns)
                ).all(axis=1)
            ]
            amdt_idx_list = df_group["amdt_idx"].tolist()

            for idx, label in enumerate(clusters):
                if label == -1:  # Ignore noise points
                    continue
                if label not in clustered_strings:
                    clustered_strings[label] = []
                clustered_strings[label].append(amdt_idx_list[idx])

            # Filter out singleton clusters
            self.tfidf_clusters_per_group[group_key] = [
                cluster for cluster in clustered_strings.values() if len(cluster) > 1
            ]

        return self.tfidf_clusters_per_group

    def _get_group_dataframe(self, group_key: tuple) -> pd.DataFrame:
        """Get dataframe filtered by group key"""
        return self.amendments_df[
            (
                self.amendments_df[self.group_by_columns]
                == pd.Series(group_key, index=self.group_by_columns)
            ).all(axis=1)
        ]

    def _calculate_distance_matrix_and_similarities(
        self,
        strings: list[str],
        cluster_amdt_idx: list[int],
        similarity_percentages: dict[int, dict[int, float]],
    ) -> tuple[np.ndarray, dict[int, dict[int, float]]]:
        """
        Calculate Damerau-Levenshtein distance matrix and similarity percentages

        Args:
            strings: List of amendment text strings
            cluster_amdt_idx: List of amendment indices
            similarity_percentages: Dictionary to store similarity percentages

        Returns:
            Tuple of distance matrix and updated similarity percentages
        """
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

        return damerau_distance_matrix, similarity_percentages

    def _apply_dbscan_and_extract_clusters(
        self,
        distance_matrix: np.ndarray,
        cluster_amdt_idx: list[int],
        distance_threshold: float,
    ) -> list[list[int]]:
        """
        Apply DBSCAN on distance matrix and extract refined clusters

        Args:
            distance_matrix: Precomputed distance matrix
            cluster_amdt_idx: List of amendment indices
            distance_threshold: Threshold for DBSCAN clustering

        Returns:
            List of refined clusters (each cluster is a list of amendment indices)
        """
        # Apply DBSCAN on the refined distance matrix
        dbscan = DBSCAN(metric="precomputed", eps=distance_threshold, min_samples=2)
        refined_cluster_labels = dbscan.fit_predict(distance_matrix)

        # Extract refined clusters
        refined_clustered_strings: dict[int, list[IntIndex]] = {}
        for idx, label in enumerate(refined_cluster_labels):
            if label == -1:  # Ignore noise points
                continue
            if label not in refined_clustered_strings:
                refined_clustered_strings[label] = []
            refined_clustered_strings[label].append(cluster_amdt_idx[idx])

        # Filter out singleton clusters
        return [
            refined_cluster
            for refined_cluster in refined_clustered_strings.values()
            if len(refined_cluster) > 1
        ]

    def _process_cluster(
        self,
        df_group: pd.DataFrame,
        cluster: list[int],
        similarity_percentages: dict[int, dict[int, float]],
        distance_threshold: float,
    ) -> tuple[list[list[int]], dict[int, dict[int, float]]]:
        """
        Process a single cluster to find refined clusters

        Args:
            df_group: Dataframe filtered by group key
            cluster: List of amendment indices in the cluster
            similarity_percentages: Dictionary to store similarity percentages
            distance_threshold: Threshold for DBSCAN clustering

        Returns:
            Tuple of refined clusters and updated similarity percentages
        """
        # Get the strings and corresponding amdt_idx for the current cluster
        strings = df_group[df_group["amdt_idx"].isin(cluster)][
            self.text_column
        ].tolist()
        cluster_amdt_idx = df_group[df_group["amdt_idx"].isin(cluster)][
            "amdt_idx"
        ].tolist()

        # Calculate distance matrix and similarity percentages
        distance_matrix, updated_similarities = (
            self._calculate_distance_matrix_and_similarities(
                strings, cluster_amdt_idx, similarity_percentages
            )
        )

        # Apply DBSCAN and extract refined clusters
        refined_clusters = self._apply_dbscan_and_extract_clusters(
            distance_matrix, cluster_amdt_idx, distance_threshold
        )

        return refined_clusters, updated_similarities

    def refine_clusters_with_distance(
        self, distance_threshold: float
    ) -> tuple[dict[tuple, list[list[int]]], dict[int, dict[int, float]]]:
        """
        Refine clusters using Damerau-Levenshtein distance

        Returns:
            A tuple containing:
            - Dictionary of refined clusters
            - Dictionary of similarity percentages between amendments
        """
        group_keys = (
            self.amendments_df[self.group_by_columns]
            .drop_duplicates()
            .itertuples(index=False, name=None)
        )
        similarity_percentages: dict[int, dict[int, float]] = {}

        for group_key in group_keys:
            df_group = self._get_group_dataframe(group_key)
            refined_clusters = []

            for cluster in self.tfidf_clusters_per_group[group_key]:
                cluster_refined, similarity_percentages = self._process_cluster(
                    df_group, cluster, similarity_percentages, distance_threshold
                )
                refined_clusters.extend(cluster_refined)

            self.final_clusters_per_group[group_key] = refined_clusters

        return self.final_clusters_per_group, similarity_percentages
