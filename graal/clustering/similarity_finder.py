import logging
from typing import Any, Optional

import numpy as np
import pandas as pd
from rapidfuzz.distance import DamerauLevenshtein
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from graal.custom_types import IntIndex


class SimilarityFinder:
    def __init__(
        self,
        old_amendments_df: pd.DataFrame,
        new_amendments_df: pd.DataFrame,
        group_by_columns: Optional[list[str]] = None,
    ):
        self.old_amendments_df = old_amendments_df
        self.new_amendments_df = new_amendments_df
        self.group_by_columns = group_by_columns

    def clusterize_similar_amdts(
        self,
        column_used_for_clustering: str = "Exposé amdt",
        clustering_similarity_threshold: float = 0.60,
    ) -> dict[IntIndex, list[IntIndex]]:
        """
        Clusterize similar documents using TF-IDF comparison on the `column_used_for_clustering` field from both old and new amendments.

        Returns: A dictionary representing clusters of documents, where keys are the amdt_idx of new
        amendments and values are lists of amdt_idx of similar old amendments. This will be used to
        identify the best matches in subsequent steps.
        """
        logging.info(
            f'Pre-filtering similar "{column_used_for_clustering}" for optimization...'
        )

        if self.group_by_columns:
            grouped_old_df = self.old_amendments_df.groupby(
                self.group_by_columns
                if len(self.group_by_columns) > 1
                else self.group_by_columns[0]
            )
            grouped_new_df = self.new_amendments_df.groupby(
                self.group_by_columns
                if len(self.group_by_columns) > 1
                else self.group_by_columns[0]
            )
            clusters = {}

            for group_key, old_group_df in grouped_old_df:
                if group_key in grouped_new_df.groups:
                    new_group_df = grouped_new_df.get_group(group_key)
                    group_clusters = SimilarityFinder.tf_idf_filtering(
                        old_amdt_values=old_group_df[
                            column_used_for_clustering
                        ].tolist(),
                        new_amd_values=new_group_df[
                            column_used_for_clustering
                        ].tolist(),
                        threshold=clustering_similarity_threshold,
                    )
                    # Transform indices into corresponding amdt_idx
                    group_clusters = {
                        new_group_df.iloc[new_idx]["amdt_idx"]: [
                            old_group_df.iloc[old_idx]["amdt_idx"]
                            for old_idx in old_indices
                        ]
                        for new_idx, old_indices in group_clusters.items()
                    }
                    clusters.update(group_clusters)
        else:
            clusters = SimilarityFinder.tf_idf_filtering(
                old_amdt_values=self.old_amendments_df[
                    column_used_for_clustering
                ].tolist(),
                new_amd_values=self.new_amendments_df[
                    column_used_for_clustering
                ].tolist(),
                threshold=clustering_similarity_threshold,
            )
            # Transform indices into corresponding amdt_idx
            clusters = {
                self.new_amendments_df.iloc[new_idx]["amdt_idx"]: [
                    self.old_amendments_df.iloc[old_idx]["amdt_idx"]
                    for old_idx in old_indices
                ]
                for new_idx, old_indices in clusters.items()
            }

        list_lengths = [len(docs) for docs in clusters.values()]
        if list_lengths:
            average_length = sum(list_lengths) / len(list_lengths)
            logging.info(
                f'Clustering: Average number of potential matches per amendment for "{column_used_for_clustering}": {average_length}'
            )
        else:
            logging.info(
                f'Clustering: Average number of potential matches per amendment for "{column_used_for_clustering}": 0'
            )
        return clusters

    def find_best_matches(
        self,
        column_used_for_similarity: str,
        clusters: dict[IntIndex, list[IntIndex]],
        fuzzy_match_similarity_threshold: float,
        similarity_threshold_overrides: dict[str, float],
    ) -> dict:
        if clusters is None:
            raise ValueError(
                "You need to prefilter similar documents (with `prefilter_similar_docs`) before finding the best matches."
            )
        old_amdt_data = {
            "text": dict(
                zip(
                    self.old_amendments_df["amdt_idx"],
                    self.old_amendments_df[column_used_for_similarity],
                )
            ),
            "comparison_value": {
                old_amdt_idx: -old_amdt_date
                for old_amdt_idx, old_amdt_date in zip(
                    self.old_amendments_df["amdt_idx"],
                    self.old_amendments_df["timestamp"],
                )
            },
            "response": dict(
                zip(
                    self.old_amendments_df["amdt_idx"],
                    self.old_amendments_df["Réponse"],
                )
            ),
        }
        new_amdt_data = {
            "text": dict(
                zip(
                    self.new_amendments_df["amdt_idx"],
                    self.new_amendments_df[column_used_for_similarity],
                )
            )
        }
        logging.info("Looking for best matches on pre-filtered amendments...")
        closest_docs = self.find_best_matching_docs(
            clusters=clusters,
            new_amdt_data=new_amdt_data,
            old_amdt_data=old_amdt_data,
            fuzzy_match_similarity_threshold=fuzzy_match_similarity_threshold,
            similarity_threshold_overrides=similarity_threshold_overrides,
        )

        for _, doc_info in closest_docs.items():
            doc_info["column_used_for_comparison"] = column_used_for_similarity

        logging.info(
            f"Fuzzy match with '{column_used_for_similarity}' column:\n\tFound matches in previous lectures for {len(closest_docs)} amendments"
        )
        return closest_docs

    @staticmethod
    def tf_idf_filtering(
        old_amdt_values: list[str],
        new_amd_values: list[str],
        threshold: float = 0.4,
    ) -> dict[IntIndex, list[IntIndex]]:
        # Combine old and new documents for TF-IDF vectorization
        all_docs = old_amdt_values + new_amd_values

        # Calculate TF-IDF vectors
        vectorizer = TfidfVectorizer()
        tfidf_matrix = vectorizer.fit_transform(all_docs)

        # Split the TF-IDF matrix into old and new parts
        db_tfidf_matrix = tfidf_matrix[: len(old_amdt_values)]
        to_filter_tfidf_matrix = tfidf_matrix[len(old_amdt_values) :]

        # Calculate cosine similarity
        cosine_sim_matrix = cosine_similarity(to_filter_tfidf_matrix, db_tfidf_matrix)

        # Find candidates using cosine similarity
        similar_doc_indices = {}
        for index, sim_vector in enumerate(cosine_sim_matrix):
            similar_docs = np.where(sim_vector >= threshold)[0].tolist()
            if similar_docs:
                similar_doc_indices[index] = similar_docs

        return similar_doc_indices

    @staticmethod
    def find_best_matching_docs(
        clusters: dict[IntIndex, list[IntIndex]],
        new_amdt_data: dict,
        old_amdt_data: dict,
        fuzzy_match_similarity_threshold: float,
        similarity_threshold_overrides: dict[str, float],
    ) -> dict[IntIndex, dict[str, Any]]:
        old_amdt_data_texts = old_amdt_data["text"]
        old_amdt_data_responses = old_amdt_data["response"]
        old_amdt_data_comparison_values = old_amdt_data["comparison_value"]
        new_amdt_data_texts = new_amdt_data["text"]

        closest_docs = {}

        for new_amdt_idx, old_amdt_data_indices in clusters.items():
            new_amdt_data_text = new_amdt_data_texts[new_amdt_idx]

            best_doc_amdt_idx = None
            min_comparison_value = float("inf")
            best_similarity_ratio = 0.0
            best_response_length = 0
            for old_amdt_data_idx in old_amdt_data_indices:
                comparison_value = old_amdt_data_comparison_values[old_amdt_data_idx]

                distance = DamerauLevenshtein.distance(
                    new_amdt_data_text, old_amdt_data_texts[old_amdt_data_idx]
                )

                current_response_length = (
                    len(old_amdt_data_responses[old_amdt_data_idx])
                    if pd.notna(old_amdt_data_responses[old_amdt_data_idx])
                    else 0
                )

                cur_doc_text = old_amdt_data_texts[old_amdt_data_idx]
                cur_text_length = len(cur_doc_text)
                cur_similarity_ratio = (cur_text_length - distance) / cur_text_length

                threshold_ratio = fuzzy_match_similarity_threshold
                for key in similarity_threshold_overrides:
                    if new_amdt_data_text.startswith(key):
                        threshold_ratio = similarity_threshold_overrides[key]
                        break

                # We want to prioritize responses that are not empty while still meeting the similarity ratio threshold
                if cur_similarity_ratio >= threshold_ratio:
                    if (
                        best_response_length == 0 and current_response_length > 0
                    ) or min_comparison_value > comparison_value:
                        best_response_length = current_response_length
                        best_doc_amdt_idx = old_amdt_data_idx
                        min_comparison_value = comparison_value
                        best_similarity_ratio = cur_similarity_ratio

            if best_doc_amdt_idx is not None:
                closest_docs[new_amdt_idx] = {
                    "best_matching_doc_amdt_idx": best_doc_amdt_idx,
                    "similarity_ratio": best_similarity_ratio,
                }
        return closest_docs
