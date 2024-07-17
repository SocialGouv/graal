import json

import pandas as pd
from rapidfuzz.distance import DamerauLevenshtein
from sklearn.cluster import DBSCAN
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class PLFSSClusterFinder:
    def __init__(self, preprocessed_amendments_df: pd.DataFrame):
        self.preprocessed_amendments_df = preprocessed_amendments_df.copy()
        self.vectorizer = TfidfVectorizer()
        self.vectors_per_lecture = {}
        self.distance_matrix_per_lecture = {}
        self.tfidf_clusters_per_lecture = {}
        self.final_clusters_per_lecture = {}

    def _vectorize_data(self) -> None:
        print("Converting strings to TF-IDF vectors for all data...\n")
        strings = self.preprocessed_amendments_df["Corps amdt"].tolist()
        self.vectorizer.fit(strings)

    def _transform_lecture_group(self, lecture_group) -> None:
        print(f"Transforming data for lecture: {lecture_group}...")
        df_group = self.preprocessed_amendments_df[
            self.preprocessed_amendments_df["Lecture"] == lecture_group
        ]
        strings = df_group["Corps amdt"].tolist()
        self.vectors_per_lecture[lecture_group] = self.vectorizer.transform(strings)

    def _compute_distance_matrix(self, lecture_group) -> None:
        print(f"Computing cosine similarity matrix for lecture: {lecture_group}...")
        similarity_matrix = cosine_similarity(self.vectors_per_lecture[lecture_group])
        distance_matrix = 1 - similarity_matrix
        distance_matrix[distance_matrix < 0] = 0  # Ensure no negative values
        self.distance_matrix_per_lecture[lecture_group] = distance_matrix

    def find_similarity_clusters(self, eps=0.5, min_samples=2) -> pd.DataFrame:
        self._vectorize_data()
        lecture_groups = self.preprocessed_amendments_df["Lecture"].unique()
        for lecture_group in lecture_groups:
            self._transform_lecture_group(lecture_group)
            self._compute_distance_matrix(lecture_group)
            print(f"Finding clusters for lecture: {lecture_group}...")
            dbscan = DBSCAN(metric="precomputed", eps=eps, min_samples=min_samples)
            clusters = dbscan.fit_predict(
                self.distance_matrix_per_lecture[lecture_group]
            )

            # Extract clusters
            clustered_strings = {}
            for idx, label in enumerate(clusters):
                if label == -1:  # Ignore noise points
                    continue
                if label not in clustered_strings:
                    clustered_strings[label] = []
                clustered_strings[label].append(idx)

            # Filter out singleton clusters
            self.tfidf_clusters_per_lecture[lecture_group] = [
                cluster for cluster in clustered_strings.values() if len(cluster) > 1
            ]
            print(
                f"Number of clusters for lecture {lecture_group}: {len(self.tfidf_clusters_per_lecture[lecture_group])}\n"
            )

        return self.tfidf_clusters_per_lecture

    def refine_clusters_with_exact_match(self, threshold: float = 0.01) -> pd.DataFrame:
        lecture_groups = self.preprocessed_amendments_df["Lecture"].unique()
        for lecture_group in lecture_groups:
            print(
                f'Refining clusters for lecture "{lecture_group}" with Damerau-Levenshtein distance...'
            )
            df_group = self.preprocessed_amendments_df[
                self.preprocessed_amendments_df["Lecture"] == lecture_group
            ]

            refined_clusters = []
            for cluster in self.tfidf_clusters_per_lecture[lecture_group]:
                strings = df_group.iloc[cluster]["Corps amdt"].tolist()
                n = len(strings)
                damerau_distance_matrix = [[0] * n for _ in range(n)]

                for i in range(n):
                    for j in range(i + 1, n):
                        distance = DamerauLevenshtein.distance(strings[i], strings[j])
                        normalized_distance = distance / max(
                            len(strings[i]), len(strings[j])
                        )
                        damerau_distance_matrix[i][j] = normalized_distance
                        damerau_distance_matrix[j][i] = normalized_distance

                # Apply DBSCAN on the refined distance matrix
                dbscan = DBSCAN(metric="precomputed", eps=threshold, min_samples=2)
                refined_cluster_labels = dbscan.fit_predict(damerau_distance_matrix)

                # Extract refined clusters
                refined_clustered_strings = {}
                for idx, label in enumerate(refined_cluster_labels):
                    if label == -1:  # Ignore noise points
                        continue
                    if label not in refined_clustered_strings:
                        refined_clustered_strings[label] = []
                    refined_clustered_strings[label].append(cluster[idx])

                # Filter out singleton clusters
                refined_clusters.extend(
                    [
                        refined_cluster
                        for refined_cluster in refined_clustered_strings.values()
                        if len(refined_cluster) > 1
                    ]
                )

            self.final_clusters_per_lecture[lecture_group] = refined_clusters
            print(
                f"Number of refined clusters for lecture {lecture_group}: {len(self.final_clusters_per_lecture[lecture_group])}\n"
            )

        return self.final_clusters_per_lecture
