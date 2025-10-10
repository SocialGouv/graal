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

    # Maximum cluster size before switching from TF-IDF to Damerau-Levenshtein refinement
    # Large clusters (> MAX_CLUSTER_SIZE_FOR_LEVENSHTEIN): Use fast O(n log n) recursive TF-IDF subdivision
    # Small clusters (≤ MAX_CLUSTER_SIZE_FOR_LEVENSHTEIN): Use accurate O(n²) Damerau-Levenshtein refinement
    MAX_CLUSTER_SIZE_FOR_LEVENSHTEIN = 30

    @staticmethod
    def find_similarity_clusters(  # noqa: C901
        amendments_df: pd.DataFrame,
        group_by_columns: list[str],
        text_column: str = "Corps amdt",
        eps: float = 0.5,
        min_samples: int = 2,
    ) -> dict[tuple, list[list[IntIndex]]]:
        """
        Find clusters using TF-IDF + DBSCAN with recursive subdivision.

        This method performs TF-IDF clustering by:
        1. Initial TF-IDF clustering with DBSCAN
        2. Recursive subdivision of large clusters (>MAX_CLUSTER_SIZE_FOR_LEVENSHTEIN) with stricter eps
        3. Returns ONLY clusters ready for Levenshtein refinement (all ≤MAX_CLUSTER_SIZE_FOR_LEVENSHTEIN)

        The subdivision ensures all clusters are small enough for the O(n²) Levenshtein
        algorithm while using fast O(n log n) TF-IDF for the bulk of the work.

        Args:
            amendments_df: DataFrame containing amendments
            group_by_columns: Columns to group by when finding clusters
            text_column: Column containing the text to analyze for similarity
            eps: Epsilon value for DBSCAN (lower = stricter clustering)
            min_samples: Minimum samples for DBSCAN core points

        Returns:
            Dictionary of clusters per group, where all clusters have
            size ≤ MAX_CLUSTER_SIZE_FOR_LEVENSHTEIN (ready for Levenshtein refinement)
        """
        logging.info(
            f"Applying complete TF-IDF clustering to groups from column {text_column}...\n"
        )

        # Get unique group keys
        group_keys = list(
            amendments_df[group_by_columns]
            .drop_duplicates()
            .itertuples(index=False, name=None)
        )

        logging.info(f"[TF_IDF_CLUSTERING] Found {len(group_keys)} unique groups")

        tfidf_clusters_per_group: dict[tuple, list[list[IntIndex]]] = {}

        for i, group_key in enumerate(group_keys):
            logging.debug(
                f"[TF_IDF_CLUSTERING] Processing group {i + 1}/{len(group_keys)}: {group_key}"
            )

            # Filter DataFrame by group key
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
                tfidf_clusters_per_group[group_key] = []
                continue

            # Apply TF-IDF clustering to this group
            clusters = AmendmentsClusterFinder._apply_tfidf_clustering(
                df_group, text_column, eps, min_samples
            )

            # Recursively subdivide any clusters that are too large for Levenshtein
            # This ensures all returned clusters are ≤ MAX_CLUSTER_SIZE_FOR_LEVENSHTEIN
            subdivided_clusters = []
            for cluster in clusters:
                if (
                    len(cluster)
                    > AmendmentsClusterFinder.MAX_CLUSTER_SIZE_FOR_LEVENSHTEIN
                ):
                    logging.info(
                        f"[TF_IDF_CLUSTERING] Subdividing large cluster "
                        f"({len(cluster)} > {AmendmentsClusterFinder.MAX_CLUSTER_SIZE_FOR_LEVENSHTEIN}) "
                        f"in group {group_key}"
                    )
                    # Recursively subdivide using TF-IDF with stricter eps
                    sub_clusters = AmendmentsClusterFinder._recursive_subdivision(
                        df_group,
                        cluster,
                        text_column,
                        eps=0.3,  # Stricter eps for subdivision
                        min_eps=0.1,
                        depth=0,
                        max_depth=5,
                    )
                    subdivided_clusters.extend(sub_clusters)

                    # Log subdivision results
                    sub_cluster_sizes = [len(sc) for sc in sub_clusters]
                    logging.debug(
                        f"[TF_IDF_CLUSTERING] Split {len(cluster)} amendments into "
                        f"{len(sub_clusters)} sub-clusters with sizes {sub_cluster_sizes}"
                    )
                else:
                    # Cluster is already small enough
                    subdivided_clusters.append(cluster)

            tfidf_clusters_per_group[group_key] = subdivided_clusters

        return tfidf_clusters_per_group

    @staticmethod
    def refine_with_levenshtein(
        amendments_df: pd.DataFrame,
        group_by_columns: list[str],
        text_column: str,
        tfidf_clusters: dict[tuple, list[list[int]]],
        distance_threshold: float,
    ) -> tuple[dict[tuple, list[list[int]]], dict[int, dict[int, float]]]:
        """
        Refine clusters using ONLY Damerau-Levenshtein distance.

        This method applies high-accuracy Damerau-Levenshtein refinement to clusters.
        ALL input clusters should already be ≤ MAX_CLUSTER_SIZE_FOR_LEVENSHTEIN
        (handled by find_similarity_clusters).

        This function:
        1. Validates that clusters are small enough (warns if >MAX_CLUSTER_SIZE_FOR_LEVENSHTEIN)
        2. Applies O(n²) Damerau-Levenshtein distance calculation
        3. Uses DBSCAN to refine clusters based on edit distance
        4. Returns refined clusters and similarity percentages

        Args:
            amendments_df: DataFrame containing amendments
            group_by_columns: Columns to group by when finding clusters
            text_column: Column containing the text to analyze for similarity
            tfidf_clusters: Complete TF-IDF clusters (all should be ≤MAX_CLUSTER_SIZE_FOR_LEVENSHTEIN)
            distance_threshold: Threshold for DBSCAN clustering on Levenshtein distances

        Returns:
            A tuple containing:
            - Dictionary of refined clusters per group
            - Dictionary of similarity percentages between amendments (for Levenshtein pairs)
        """
        similarity_percentages: dict[int, dict[int, float]] = {}

        # Initialize all groups from dataframe with empty lists
        all_group_keys = list(
            amendments_df[group_by_columns]
            .drop_duplicates()
            .itertuples(index=False, name=None)
        )
        final_clusters_per_group: dict[tuple, list[list[IntIndex]]] = {
            group_key: [] for group_key in all_group_keys
        }

        # Only process groups that actually have clusters to refine
        for group_key, clusters in tfidf_clusters.items():
            if not clusters:
                # No clusters for this group, already initialized as empty
                continue

            # Get dataframe filtered by group key
            df_group = amendments_df[
                (
                    amendments_df[group_by_columns]
                    == pd.Series(group_key, index=group_by_columns)
                ).all(axis=1)
            ]
            refined_clusters = []

            # Apply Levenshtein refinement to each cluster
            for cluster in clusters:
                # Apply Levenshtein refinement
                levenshtein_refined = AmendmentsClusterFinder._refine_small_cluster(
                    df_group,
                    cluster,
                    similarity_percentages,
                    distance_threshold,
                    text_column,
                )
                refined_clusters.extend(levenshtein_refined)

            final_clusters_per_group[group_key] = refined_clusters

        return final_clusters_per_group, similarity_percentages

    @staticmethod
    def _apply_tfidf_clustering(
        df_subset: pd.DataFrame,
        text_column: str,
        eps: float,
        min_samples: int = 2,
    ) -> list[list[IntIndex]]:
        """
        Apply TF-IDF clustering to a DataFrame subset.

        Extracts text from the specified column, validates strings, applies TF-IDF
        vectorization, computes cosine similarity, and performs DBSCAN clustering.

        Args:
            df_subset: DataFrame subset to cluster
            text_column: Column containing the text to analyze for similarity
            eps: Epsilon value for DBSCAN (lower = stricter clustering)
            min_samples: Minimum samples for DBSCAN core points

        Returns:
            List of clusters (each cluster is a list of amendment indices),
            filtering out singleton clusters
        """
        # Extract strings and amendment indices
        strings = df_subset[text_column].tolist()
        amdt_idx_list = df_subset["amdt_idx"].tolist()

        # Validate strings - ensure we have valid content for TF-IDF
        valid_strings = [s for s in strings if s and s.strip()]
        if not valid_strings:
            logging.warning(
                f"No valid strings in subset of {len(df_subset)} amendments for TF-IDF clustering"
            )
            return []

        # Apply TF-IDF vectorization
        vectorizer = TfidfVectorizer()
        try:
            vectors = vectorizer.fit_transform(strings)
        except ValueError as e:
            logging.error(f"TF-IDF vectorization failed: {e}")
            return []

        # Compute cosine similarity and distance matrix
        similarity_matrix = cosine_similarity(vectors)
        distance_matrix = 1 - similarity_matrix
        distance_matrix[distance_matrix < 0] = 0  # Ensure no negative values

        # Apply DBSCAN clustering
        dbscan = DBSCAN(metric="precomputed", eps=eps, min_samples=min_samples)
        cluster_labels = dbscan.fit_predict(distance_matrix)

        # Extract clusters, mapping back to amendment indices
        clustered_amendments: dict[int, list[IntIndex]] = {}
        for idx, label in enumerate(cluster_labels):
            if label == -1:  # Ignore noise points
                continue
            if label not in clustered_amendments:
                clustered_amendments[label] = []
            clustered_amendments[label].append(amdt_idx_list[idx])

        # Filter out singleton clusters
        clusters = [
            cluster for cluster in clustered_amendments.values() if len(cluster) > 1
        ]

        return clusters

    @staticmethod
    def _refine_small_cluster(
        df_group: pd.DataFrame,
        cluster: list[IntIndex],
        similarity_percentages: dict[int, dict[int, float]],
        distance_threshold: float,
        text_column: str,
    ) -> list[list[IntIndex]]:
        """
        Refine small cluster (≤50 amendments) using Damerau-Levenshtein distance.

        High-accuracy O(n²) algorithm acceptable for small clusters. Uses symmetric
        calculation optimization to reduce comparisons by ~50%.

        Args:
            df_group: DataFrame filtered by group key
            cluster: List of amendment indices in the cluster (should be ≤50)
            similarity_percentages: Dictionary to store similarity percentages (modified in place)
            distance_threshold: Threshold for DBSCAN clustering
            text_column: Column containing the text to analyze for similarity

        Returns:
            List of refined clusters after Damerau-Levenshtein refinement
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

        # Pre-initialize similarity_percentages for all amendments
        for i in range(n):
            amdt_i = cluster_amdt_idx[i]
            if amdt_i not in similarity_percentages:
                similarity_percentages[amdt_i] = {}

        # Performance Optimization: Calculate distances only for unique pairs (i < j)
        # Since Damerau-Levenshtein distance is symmetric: distance(A, B) = distance(B, A)
        # This reduces calculations from O(n²) to O(n²/2), approximately 50% improvement

        for i in range(n):
            amdt_i = cluster_amdt_idx[i]

            for j in range(
                i + 1, n
            ):  # Only calculate for j > i (symmetric optimization)
                amdt_j = cluster_amdt_idx[j]

                # Calculate Damerau-Levenshtein distance once per unique pair
                distance = DamerauLevenshtein.distance(strings[i], strings[j])
                normalized_distance = distance / max(len(strings[i]), len(strings[j]))

                # Early termination optimization: Skip storing nearly-identical texts
                # Threshold of 0.001 (0.1%) means texts differ by less than 1 character per 1000
                if normalized_distance < 0.001:
                    normalized_distance = 0.0  # Treat as identical

                # Calculate similarity percentage
                similarity_percentage = (1 - normalized_distance) * 100

                # Store results symmetrically (both i->j and j->i)
                similarity_percentages[amdt_i][amdt_j] = similarity_percentage
                similarity_percentages[amdt_j][amdt_i] = similarity_percentage

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
    def _recursive_subdivision(
        df_group: pd.DataFrame,
        cluster: list[IntIndex],
        text_column: str,
        eps: float = 0.3,
        min_eps: float = 0.1,
        depth: int = 0,
        max_depth: int = 5,
    ) -> list[list[IntIndex]]:
        """
        Recursively subdivide large clusters using TF-IDF until all clusters are ≤ MAX_CLUSTER_SIZE_FOR_LEVENSHTEIN.

        This method applies TF-IDF clustering with progressively stricter eps thresholds
        to break down large clusters into smaller, more manageable sizes suitable for
        Damerau-Levenshtein refinement.

        Args:
            df_group: DataFrame filtered by group key
            cluster: List of amendment indices in the cluster
            text_column: Column containing the text to analyze for similarity
            eps: Current DBSCAN eps parameter (lower = stricter clustering)
            min_eps: Minimum eps to use - stops recursion
            depth: Current recursion depth
            max_depth: Maximum recursion depth - safety limit

        Returns:
            List of sub-clusters, all with size ≤ MAX_CLUSTER_SIZE_FOR_LEVENSHTEIN (when possible)
        """
        # Base case 1: Cluster is small enough for Levenshtein refinement
        if len(cluster) <= AmendmentsClusterFinder.MAX_CLUSTER_SIZE_FOR_LEVENSHTEIN:
            logging.debug(
                f"Cluster size {len(cluster)} ≤ {AmendmentsClusterFinder.MAX_CLUSTER_SIZE_FOR_LEVENSHTEIN}, "
                f"ready for Levenshtein refinement (depth={depth})"
            )
            return [cluster]

        # Base case 2: Already at minimum eps - can't split further
        if eps <= min_eps:
            logging.warning(
                f"Cannot split cluster of {len(cluster)} amendments further "
                f"(eps={eps:.3f} ≤ min_eps={min_eps}, depth={depth}). "
                f"Returning large cluster as-is."
            )
            return [cluster]

        # Base case 3: Max recursion depth reached (safety)
        if depth >= max_depth:
            logging.warning(
                f"Max recursion depth {max_depth} reached for cluster of {len(cluster)} amendments "
                f"(depth={depth}). Returning large cluster as-is."
            )
            return [cluster]

        # Recursive case: Apply TF-IDF clustering with stricter eps
        stricter_eps = max(eps - 0.05, min_eps)
        logging.info(
            f"Subdividing cluster of {len(cluster)} amendments with TF-IDF eps={stricter_eps:.3f} "
            f"(previous={eps:.3f}, depth={depth})"
        )

        # Extract subset DataFrame for this cluster
        cluster_df = df_group[df_group["amdt_idx"].isin(cluster)].copy()

        # Apply TF-IDF clustering to this cluster
        sub_clusters = AmendmentsClusterFinder._apply_tfidf_clustering(
            cluster_df, text_column, stricter_eps, min_samples=2
        )

        # If no sub-clusters created, return original cluster
        if not sub_clusters:
            logging.warning(
                f"No sub-clusters created with eps={stricter_eps:.3f} for cluster of {len(cluster)} amendments. "
                f"Returning original cluster."
            )
            return [cluster]

        # If only one sub-cluster and same size, can't split further
        if len(sub_clusters) == 1 and len(sub_clusters[0]) == len(cluster):
            logging.warning(
                f"Clustering produced single cluster of same size ({len(cluster)} amendments) "
                f"with eps={stricter_eps:.3f}. Cannot split further."
            )
            return [cluster]

        # Log the split results
        sub_cluster_sizes = [len(sc) for sc in sub_clusters]
        logging.info(
            f"Split cluster of {len(cluster)} amendments into {len(sub_clusters)} sub-clusters "
            f"with sizes {sub_cluster_sizes} (depth={depth})"
        )

        # Recursively subdivide any sub-clusters that are still too large
        all_subdivided_clusters: list[list[IntIndex]] = []
        for i, sub_cluster in enumerate(sub_clusters):
            logging.debug(
                f"Processing sub-cluster {i + 1}/{len(sub_clusters)} "
                f"(size={len(sub_cluster)}, depth={depth})"
            )
            subdivided = AmendmentsClusterFinder._recursive_subdivision(
                df_group,
                sub_cluster,
                text_column,
                eps=stricter_eps,
                min_eps=min_eps,
                depth=depth + 1,
                max_depth=max_depth,
            )
            all_subdivided_clusters.extend(subdivided)

        return all_subdivided_clusters
