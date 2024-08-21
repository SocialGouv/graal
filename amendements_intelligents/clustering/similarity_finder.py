import pandas as pd

from amendements_intelligents.types import IntIndex
from amendements_intelligents.utils.content_similarity_evaluator import (
    ContentSimilarityEvaluator,
)


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
        self, column_used_for_comparison: str = "Exposé amdt", threshold=0.7
    ) -> dict[IntIndex, list[IntIndex]]:
        """
        Pre-filters similar documents based on a TF-IDF comparison of the `column_used_for_comparison` in the old and new amendments.

        Internally, it saves a dictionary with keys being the index of the new amendment and values being a list of indices of the old amendments that are similar. It will be used to find the best matches later on.

        Return: The dictionnary mentionned above.
        """
        print("Pre-filtering similar documents for optimization...")
        self.similar_doc_indices = ContentSimilarityEvaluator.tf_idf_filtering(
            documents_to_search=self.old_amendments_df[
                column_used_for_comparison
            ].tolist(),
            documents_to_filter=self.new_amendments_df[
                column_used_for_comparison
            ].tolist(),
            threshold=threshold,
        )
        list_lengths = [len(docs) for docs in self.similar_doc_indices.values()]
        average_length = sum(list_lengths) / len(list_lengths)
        print(f"Average number of potential matches per amendment: {average_length}")
        return self.similar_doc_indices

    def find_best_matches(
        self, column_used_for_comparison: str = "Exposé amdt"
    ) -> dict:
        if self.similar_doc_indices is None:
            raise ValueError(
                "You need to prefilter similar documents (with `prefilter_similar_docs`) before finding the best matches."
            )
        old_amendments = {
            "text": self.old_amendments_df[column_used_for_comparison],
            "amdt_idx": self.old_amendments_df["amdt_idx"],
            "comparison_value": -self.old_amendments_df["Year"],
        }
        new_amendments = self.new_amendments_df[column_used_for_comparison]
        print("Looking for best matches on pre-filtered amendments...")
        closest_docs = ContentSimilarityEvaluator.find_best_matching_docs(
            similar_doc_indices=self.similar_doc_indices,
            left_docs=new_amendments,
            right_docs=old_amendments,
            default_threshold_ratio=self.default_threshold_ratio,
            threshold_ratio_mappings=self.threshold_ratio_mappings,
        )

        for _, doc_info in closest_docs.items():
            doc_info["column_used_for_comparison"] = column_used_for_comparison

        print(f"Found matches in previous PLFSS for {len(closest_docs)} amendments")
        return closest_docs
