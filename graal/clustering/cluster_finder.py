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

    def __init__(self, amendments_df: pd.DataFrame, group_by_columns: list[str]):
        self.amendments_df = amendments_df.copy()
        self.group_by_columns = group_by_columns
        self.vectorizer = TfidfVectorizer()
        self.vectors_per_group: dict[tuple, spmatrix] = {}
        self.distance_matrix_per_group: dict[tuple, ndarray] = {}
        self.tfidf_clusters_per_group: dict[tuple, list[list[IntIndex]]] = {}
        self.final_clusters_per_group: dict[tuple, list[list[IntIndex]]] = {}

    def _vectorize_data(self) -> None:
        """Convert strings to TF-IDF vectors for all Corps amdt"""
        logging.info("Converting strings to TF-IDF vectors for all data...\n")
        strings = self.amendments_df["Corps amdt"].tolist()
        self.vectorizer.fit(strings)

    def _transform_group(self, group_key: tuple) -> None:
        """Transform strings to TF-IDF vectors for a specific group"""
        df_group = self.amendments_df[
            (
                self.amendments_df[self.group_by_columns]
                == pd.Series(group_key, index=self.group_by_columns)
            ).all(axis=1)
        ]
        strings = df_group["Corps amdt"].tolist()
        self.vectors_per_group[group_key] = self.vectorizer.transform(strings)

    def _compute_distance_matrix(self, group_key: tuple) -> None:
        """Compute cosine similarity matrix for a specific group"""
        similarity_matrix = cosine_similarity(self.vectors_per_group[group_key])
        distance_matrix = 1 - similarity_matrix
        distance_matrix[distance_matrix < 0] = 0  # Ensure no negative values
        self.distance_matrix_per_group[group_key] = distance_matrix

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

    def refine_clusters_with_distance(
        self, distance_threshold: float
    ) -> dict[tuple, list[list[int]]]:
        """Refine clusters using Damerau-Levenshtein distance"""
        group_keys = (
            self.amendments_df[self.group_by_columns]
            .drop_duplicates()
            .itertuples(index=False, name=None)
        )
        for group_key in group_keys:
            df_group = self.amendments_df[
                (
                    self.amendments_df[self.group_by_columns]
                    == pd.Series(group_key, index=self.group_by_columns)
                ).all(axis=1)
            ]

            refined_clusters = []
            for cluster in self.tfidf_clusters_per_group[group_key]:
                # Get the strings and corresponding amdt_idx for the current cluster
                strings = df_group[df_group["amdt_idx"].isin(cluster)][
                    "Corps amdt"
                ].tolist()
                cluster_amdt_idx = df_group[df_group["amdt_idx"].isin(cluster)][
                    "amdt_idx"
                ].tolist()
                n = len(strings)
                damerau_distance_matrix = np.zeros((n, n))

                for i in range(n):
                    for j in range(i + 1, n):
                        distance = DamerauLevenshtein.distance(strings[i], strings[j])
                        normalized_distance = distance / max(
                            len(strings[i]), len(strings[j])
                        )
                        damerau_distance_matrix[i][j] = normalized_distance
                        damerau_distance_matrix[j][i] = normalized_distance

                # Apply DBSCAN on the refined distance matrix
                dbscan = DBSCAN(
                    metric="precomputed", eps=distance_threshold, min_samples=2
                )
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
                refined_clusters.extend(
                    [
                        refined_cluster
                        for refined_cluster in refined_clustered_strings.values()
                        if len(refined_cluster) > 1
                    ]
                )

            self.final_clusters_per_group[group_key] = refined_clusters

        return self.final_clusters_per_group
