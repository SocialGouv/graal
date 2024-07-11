import os
import time

import pandas as pd
from pydantic import FilePath

from amendements_intelligents.utils.content_similarity_evaluator import (
    ContentSimilarityEvaluator,
)
from amendements_intelligents.utils.plfss_text_processor import PLFSSTextProcessor


class PLFSSDataManager:
    def __init__(self, input_file: FilePath):
        self.input_file = input_file
        self.min_length_expose_to_process = 50
        self.previous_plfss_df = None
        self.amendments_to_process_df = None
        self.new_amendments_df = None
        self.old_amendments_df = None
        self._load_data()
        self._simulate_new_amendments()

    def _load_data(self) -> None:
        # TODO: refactor this to be a dict of year to file because right now it only takes the 2024 PLFSS in
        self.previous_plfss_df = pd.read_json(self.input_file)
        self.previous_plfss_df["Year"] = 2024
        print(
            f"Loaded {len(self.previous_plfss_df)} previous PLFSS amendments for processing"
        )

    # TODO: remove this once we can work with real new amendments
    def _simulate_new_amendments(self) -> None:
        # Simulate new amendments
        self.amendments_to_process_df = self.previous_plfss_df.sample(
            n=int(0.2 * len(self.previous_plfss_df))
        )
        self.amendments_to_process_df["Allotissement"] = None
        self.amendments_to_process_df["Identique"] = None
        self.amendments_to_process_df["Réponse"] = None
        self.amendments_to_process_df["Sort"] = None
        self.amendments_to_process_df["Commentaires"] = None
        self.previous_plfss_df = self.previous_plfss_df[
            ~self.previous_plfss_df["Numéro"].isin(
                self.amendments_to_process_df["Numéro"]
            )
        ]
        print(f"Processing {len(self.amendments_to_process_df)} new amendments...")

    def preprocess_data(self) -> None:
        """
        Goes over "Exposé des motifs" column in each dataframe and lowercase the text, remove unnecessary accents, whitespaces, etc.

        The goal is to allow for easier comparison of each Exposé des motifs.
        """
        self.old_amendments_df = PLFSSTextProcessor.preprocess_df(
            self.previous_plfss_df
        )
        self.new_amendments_df = PLFSSTextProcessor.preprocess_df(
            self.amendments_to_process_df
        )


class SimilarityFinder:
    def __init__(
        self, old_amendments_df: pd.DataFrame, new_amendments_df: pd.DataFrame
    ):
        self.old_amendments_df = old_amendments_df
        self.new_amendments_df = new_amendments_df
        self.similar_doc_indices = None

    def _prefilter_similar_docs(self) -> None:
        print("Pre-filtering similar documents for optimization...")
        self.similar_doc_indices = ContentSimilarityEvaluator.tf_idf_filtering(
            documents_to_search=self.old_amendments_df["Exposé des motifs"].tolist(),
            documents_to_filter=self.new_amendments_df["Exposé des motifs"].tolist(),
            threshold=0.7,
        )
        list_lengths = [len(docs) for docs in self.similar_doc_indices.values()]
        average_length = sum(list_lengths) / len(list_lengths)
        print(f"Average number of potential matches per amendment: {average_length}")

    def find_best_matches(self) -> dict:
        self._prefilter_similar_docs()

        old_amendments = {
            "text": self.old_amendments_df["Exposé des motifs"],
            "comparison_value": -self.old_amendments_df["Year"],
        }
        new_amendments = self.new_amendments_df["Exposé des motifs"]
        print("Looking for best matches on pre-filtered amendments...")
        closest_docs = ContentSimilarityEvaluator.find_best_matching_docs(
            similar_doc_indices=self.similar_doc_indices,
            left_docs=new_amendments,
            right_docs=old_amendments,
            threshold_ratio=0.95,
        )
        print(f"Found matches in previous PLFSS for {len(closest_docs)} amendments")
        return closest_docs


class AmendmentCopier:
    def __init__(
        self,
        new_amendments_df: pd.DataFrame,
        old_amendments_df: pd.DataFrame,
        closest_docs: dict,
    ):
        self.new_amendments_df = new_amendments_df
        self.old_amendments_df = old_amendments_df
        self.closest_docs = closest_docs

    def copy_matches_to_new_amendments(self, target_df: pd.DataFrame):
        for new_idx, closest_doc in self.closest_docs.items():
            new_amendment_numero = self.new_amendments_df.iloc[new_idx]["Numéro"]
            new_amendment_lecture = self.new_amendments_df.iloc[new_idx]["Lecture"]
            mask = (target_df["Numéro"] == new_amendment_numero) & (
                target_df["Lecture"] == new_amendment_lecture
            )
            best_match_idx = closest_doc["best_matching_doc_idx"]

            target_df.loc[mask, "Réponse"] = self.old_amendments_df.iloc[
                best_match_idx
            ]["Réponse"]

            matching_numero = self.old_amendments_df.iloc[best_match_idx]["Numéro"]
            matching_pos = self.old_amendments_df.iloc[best_match_idx]["Lecture"]
            matching_year = -closest_doc["best_matching_comparison_value"]
            target_df.loc[mask, "Commentaires"] = f"""
            Réponse copiée du PLFSS {matching_year}
            Numéro d'amendement : {matching_numero}
            Lecture : {matching_pos}
            """

            old_sort_value = self.old_amendments_df.iloc[best_match_idx]["Sort"]
            if old_sort_value and "irrecevable" in old_sort_value.lower():
                target_df.loc[mask, "Sort"] = old_sort_value
        return target_df


def main():
    start_time = time.time()

    DATA_FOLDER = os.getenv("DATA_FOLDER", "data")
    INPUT_FILE = f"{DATA_FOLDER}/PLFSS 2024.json"
    OUTPUT_FILE = f"{DATA_FOLDER}/amendments_with_similarity.xlsx"
    COLUMNS_TO_OUTPUT = [
        "Numéro",
        "Lecture",
        "Commentaires",
        "Réponse",
        "Exposé des motifs",
        "Sort",
        "Allotissement",
        "Identique",
    ]

    # Data management
    data_manager = PLFSSDataManager(input_file=INPUT_FILE)
    data_manager.preprocess_data()

    # Similarity evaluation
    similarity_evaluator = SimilarityFinder(
        old_amendments_df=data_manager.old_amendments_df,
        new_amendments_df=data_manager.new_amendments_df,
    )
    closest_docs = similarity_evaluator.find_best_matches()

    # Result processing
    result_manager = AmendmentCopier(
        new_amendments_df=data_manager.new_amendments_df,
        old_amendments_df=data_manager.old_amendments_df,
        closest_docs=closest_docs,
    )
    amendments_df = result_manager.copy_matches_to_new_amendments(
        data_manager.amendments_to_process_df
    )
    amendments_df[COLUMNS_TO_OUTPUT].to_excel(OUTPUT_FILE, index=False)
    print(f"Saved result in {OUTPUT_FILE}")

    # Print execution time
    end_time = time.time()
    execution_time = end_time - start_time
    print(f"Script execution time: {execution_time} seconds")


if __name__ == "__main__":
    main()
