from typing import Any

import numpy as np
import pandas as pd
from rapidfuzz.distance import DamerauLevenshtein
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from amendements_intelligents.types import IntIndex


class ContentSimilarityEvaluator:
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
        threshold_ratio_mappings: dict[str, float] = None,
    ) -> dict[IntIndex, dict[str, Any]]:
        right_doc_texts = right_docs["text"]
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
                        "best_matching_doc_idx": best_doc_idx,
                        "best_matching_doc_length": best_doc_length,
                        "similarity_ratio": similarity_ratio,
                    }
        return closest_docs
