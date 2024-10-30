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
        default_threshold_ratio: float = 0.60,
        threshold_ratio_mappings: Optional[dict[str, float]] = None,
    ):
        self.old_amendments_df = old_amendments_df
        self.new_amendments_df = new_amendments_df
        self.similar_doc_indices: dict[IntIndex, list[IntIndex]] = {}
        self.default_threshold_ratio = default_threshold_ratio
        self.threshold_ratio_mappings = (
            threshold_ratio_mappings if threshold_ratio_mappings is not None else {}
        )

    def prefilter_similar_docs(
        self, column_used_for_similarity: str = "Exposé amdt", threshold=0.60
    ) -> dict[IntIndex, list[IntIndex]]:
        """
        Pre-filters similar documents based on a TF-IDF comparison of the `column_used_for_similarity` in the old and new amendments.

        Internally, it saves a dictionary with keys being the amdt_idx of the new amendment and values being a list of amdt_idx of the old amendments that are similar. It will be used to find the best matches later on.

        Return: The dictionnary mentionned above.
        """
        logging.info(
            f'Pre-filtering similar "{column_used_for_similarity}" for optimization...'
        )
        self.similar_doc_indices = SimilarityFinder.tf_idf_filtering(
            old_amdt_values=self.old_amendments_df[column_used_for_similarity].tolist(),
            new_amd_values=self.new_amendments_df[column_used_for_similarity].tolist(),
            threshold=threshold,
        )
        # Transform indices into corresponding amdt_idx
        self.similar_doc_indices = {
            self.new_amendments_df.iloc[new_idx]["amdt_idx"]: [
                self.old_amendments_df.iloc[old_idx]["amdt_idx"]
                for old_idx in old_indices
            ]
            for new_idx, old_indices in self.similar_doc_indices.items()
        }
        list_lengths = [len(docs) for docs in self.similar_doc_indices.values()]
        if list_lengths:
            average_length = sum(list_lengths) / len(list_lengths)
            logging.info(
                f'Average number of potential matches per amendment for "{column_used_for_similarity}": {average_length}'
            )
        else:
            logging.info(
                f'Average number of potential matches per amendment for "{column_used_for_similarity}": 0'
            )
        return self.similar_doc_indices

    def find_best_matches(
        self, column_used_for_similarity: str = "Exposé amdt"
    ) -> dict:
        if self.similar_doc_indices is None:
            raise ValueError(
                "You need to prefilter similar documents (with `prefilter_similar_docs`) before finding the best matches."
            )
        old_amdt_data = {
            "text": {
                old_amdt_idx: old_amdt_text
                for old_amdt_idx, old_amdt_text in zip(
                    self.old_amendments_df["amdt_idx"],
                    self.old_amendments_df[column_used_for_similarity],
                )
            },
            "comparison_value": {
                old_amdt_idx: -old_amdt_date
                for old_amdt_idx, old_amdt_date in zip(
                    self.old_amendments_df["amdt_idx"],
                    self.old_amendments_df["timestamp"],
                )
            },
            "response": {
                old_amdt_idx: old_amdt_response
                for old_amdt_idx, old_amdt_response in zip(
                    self.old_amendments_df["amdt_idx"],
                    self.old_amendments_df["Réponse"],
                )
            },
        }
        new_amdt_data = {
            "text": {
                old_amdt_idx: old_amdt_text
                for old_amdt_idx, old_amdt_text in zip(
                    self.new_amendments_df["amdt_idx"],
                    self.new_amendments_df[column_used_for_similarity],
                )
            }
        }
        logging.info("Looking for best matches on pre-filtered amendments...")
        closest_docs = SimilarityFinder.find_best_matching_docs(
            similar_doc_indices=self.similar_doc_indices,
            new_amdt_data=new_amdt_data,
            old_amdt_data=old_amdt_data,
            default_threshold_ratio=self.default_threshold_ratio,
            threshold_ratio_mappings=self.threshold_ratio_mappings,
        )

        for _, doc_info in closest_docs.items():
            doc_info["column_used_for_comparison"] = column_used_for_similarity

        logging.info(
            f"Found matches in previous lectures for {len(closest_docs)} amendments"
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
        similar_doc_indices: dict[IntIndex, list[IntIndex]],
        new_amdt_data: dict,
        old_amdt_data: dict,
        default_threshold_ratio: float,
        threshold_ratio_mappings: dict[str, float],
    ) -> dict[IntIndex, dict[str, Any]]:
        old_amdt_data_texts = old_amdt_data["text"]
        old_amdt_data_responses = old_amdt_data["response"]
        old_amdt_data_comparison_values = old_amdt_data["comparison_value"]
        new_amdt_data_texts = new_amdt_data["text"]

        closest_docs = {}

        for new_amdt_idx, old_amdt_data_indices in similar_doc_indices.items():
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

                threshold_ratio = default_threshold_ratio
                for key in threshold_ratio_mappings:
                    if new_amdt_data_text.startswith(key):
                        threshold_ratio = threshold_ratio_mappings[key]
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
                    "best_matching_comparison_value": min_comparison_value,
                    "best_matching_doc_amdt_idx": best_doc_amdt_idx,
                    "similarity_ratio": best_similarity_ratio,
                }
        return closest_docs
