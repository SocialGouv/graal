import logging
from typing import Any, Optional

import numpy as np
import pandas as pd
from rapidfuzz.distance import DamerauLevenshtein
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from amendements_intelligents.types import IntIndex


class SimilarityFinder:
    def __init__(
        self,
        old_amendments_df: pd.DataFrame,
        new_amendments_df: pd.DataFrame,
        default_threshold_ratio: float = 0.75,
        threshold_ratio_mappings=None,
    ):
        self.old_amendments_df = old_amendments_df
        self.new_amendments_df = new_amendments_df
        self.similar_doc_indices: dict[IntIndex, list[IntIndex]] = {}
        self.default_threshold_ratio = default_threshold_ratio
        self.threshold_ratio_mappings = (
            threshold_ratio_mappings if threshold_ratio_mappings is not None else {}
        )

    def prefilter_similar_docs(
        self, column_used_for_similarity: str = "Exposé amdt", threshold=0.7
    ) -> dict[IntIndex, list[IntIndex]]:
        """
        Pre-filters similar documents based on a TF-IDF comparison of the `column_used_for_comparison` in the old and new amendments.

        Internally, it saves a dictionary with keys being the index of the new amendment and values being a list of indices of the old amendments that are similar. It will be used to find the best matches later on.

        Return: The dictionnary mentionned above.
        """
        logging.info(
            f'Pre-filtering similar "{column_used_for_similarity}" for optimization...'
        )
        self.similar_doc_indices = SimilarityFinder.tf_idf_filtering(
            documents_to_search=self.old_amendments_df[
                column_used_for_similarity
            ].tolist(),
            documents_to_filter=self.new_amendments_df[
                column_used_for_similarity
            ].tolist(),
            threshold=threshold,
        )
        list_lengths = [len(docs) for docs in self.similar_doc_indices.values()]
        average_length = sum(list_lengths) / len(list_lengths)
        logging.info(
            f'Average number of potential matches per amendment for "{column_used_for_similarity}": {average_length}'
        )
        return self.similar_doc_indices

    def find_best_matches(
        self, column_used_for_similarity: str = "Exposé amdt"
    ) -> dict:
        if self.similar_doc_indices is None:
            raise ValueError(
                "You need to prefilter similar documents (with `prefilter_similar_docs`) before finding the best matches."
            )
        old_amendments = {
            "text": self.old_amendments_df[column_used_for_similarity],
            "amdt_idx": self.old_amendments_df["amdt_idx"],
            "comparison_value": -self.old_amendments_df["Year"],
        }
        new_amendments = self.new_amendments_df[column_used_for_similarity]
        logging.info("Looking for best matches on pre-filtered amendments...")
        closest_docs = SimilarityFinder.find_best_matching_docs(
            similar_doc_indices=self.similar_doc_indices,
            left_docs=new_amendments,
            right_docs=old_amendments,
            default_threshold_ratio=self.default_threshold_ratio,
            threshold_ratio_mappings=self.threshold_ratio_mappings,
        )

        for _, doc_info in closest_docs.items():
            doc_info["column_used_for_comparison"] = column_used_for_similarity

        logging.info(
            f"Found matches in previous PLFSS for {len(closest_docs)} amendments"
        )
        return closest_docs

    @staticmethod
    def tf_idf_filtering(
        documents_to_search: list[str],
        documents_to_filter: list[str],
        threshold: float = 0.4,
    ) -> dict[IntIndex, list[IntIndex]]:
        # Combine old and new documents for TF-IDF vectorization
        all_docs = documents_to_search + documents_to_filter

        # Calculate TF-IDF vectors
        vectorizer = TfidfVectorizer()
        tfidf_matrix = vectorizer.fit_transform(all_docs)

        # Split the TF-IDF matrix into old and new parts
        db_tfidf_matrix = tfidf_matrix[: len(documents_to_search)]
        to_filter_tfidf_matrix = tfidf_matrix[len(documents_to_search) :]

        # Calculate cosine similarity
        cosine_sim_matrix = cosine_similarity(to_filter_tfidf_matrix, db_tfidf_matrix)

        # Find candidates using cosine similarity
        similar_doc_indices = {}
        for i, sim_vector in enumerate(cosine_sim_matrix):
            similar_docs = np.where(sim_vector >= threshold)[0].tolist()
            if similar_docs:
                similar_doc_indices[i] = similar_docs

        return similar_doc_indices

    @staticmethod
    def find_best_matching_docs(
        similar_doc_indices: dict[IntIndex, list[IntIndex]],
        left_docs: pd.DataFrame,
        right_docs: dict,
        default_threshold_ratio: float,
        threshold_ratio_mappings: Optional[dict[str, float]] = None,
    ) -> dict[IntIndex, dict[str, Any]]:
        right_doc_texts = right_docs["text"]
        right_doc_amdt_idx = right_docs["amdt_idx"]
        right_doc_comparison_values = right_docs["comparison_value"]

        closest_docs = {}

        for left_doc_idx, right_doc_indices in similar_doc_indices.items():
            left_doc_text = left_docs.iloc[left_doc_idx]

            best_doc_idx = None
            min_distance = float("inf")
            min_comparison_value = float("inf")
            for right_doc_idx in right_doc_indices:
                # The min_comparison_value is the most important filter so if we don't improve on it,
                # we can simply skip
                comparison_value = right_doc_comparison_values.iloc[right_doc_idx]

                if comparison_value > min_comparison_value:
                    continue

                distance = DamerauLevenshtein.distance(
                    left_doc_text, right_doc_texts.iloc[right_doc_idx]
                )
                if distance < min_distance:
                    min_distance = distance
                    best_doc_idx = right_doc_idx
                    min_comparison_value = comparison_value

            if best_doc_idx is not None:
                best_doc_text = right_doc_texts.iloc[best_doc_idx]
                best_doc_amdt_idx = right_doc_amdt_idx.iloc[best_doc_idx]
                best_doc_length = len(best_doc_text)
                similarity_ratio = (best_doc_length - min_distance) / best_doc_length

                threshold_ratio = default_threshold_ratio
                for key in threshold_ratio_mappings:
                    if left_doc_text.startswith(key):
                        threshold_ratio = threshold_ratio_mappings[key]
                        break

                if similarity_ratio >= threshold_ratio:
                    closest_docs[left_doc_idx] = {
                        "best_matching_comparison_value": min_comparison_value,
                        "best_matching_doc_amdt_idx": best_doc_amdt_idx,
                        "best_matching_doc_length": best_doc_length,
                        "similarity_ratio": similarity_ratio,
                    }
        return closest_docs
