import logging
import logging.config
import time

import pandas as pd
from pydantic import FilePath

from amendements_intelligents.clustering.similarity_finder import SimilarityFinder

logging.config.fileConfig("logging.conf")


class InadmissibleAmendmentHandler:
    def __init__(self, preprocessed_inadmissible_file: FilePath):
        self.preprocessed_inadmissible_file = preprocessed_inadmissible_file

    def process(self, amendments_df: pd.DataFrame):
        start_time = time.time()
        filtered_amendments_df = pd.read_pickle(self.preprocessed_inadmissible_file)
        logging.info(
            f"Loaded {len(filtered_amendments_df)} pre-processed inadmissible amendments from {self.preprocessed_inadmissible_file}"
        )

        similarity_evaluator_expose = SimilarityFinder(
            old_amendments_df=filtered_amendments_df,
            new_amendments_df=amendments_df,
            # similarity_threshold_overrides={"amendement redactionnel": 0.95},
        )
        similarity_evaluator_expose.prefilter_similar_docs(
            column_used_for_similarity="Exposé amdt",
            clustering_similarity_threshold=0.95,
        )
        closest_amdts = similarity_evaluator_expose.find_best_matches(
            column_used_for_similarity="Exposé amdt",
            exact_match_similarity_threshold=0.95,
        )

        if "Commentaires" not in amendments_df.columns:
            amendments_df["Commentaires"] = ""

        for amdt_idx, closest_doc in closest_amdts.items():
            amendment_mask = amendments_df["amdt_idx"] == amdt_idx
            best_matching_doc_amdt_idx = closest_doc["best_matching_doc_amdt_idx"]
            matching_sort = filtered_amendments_df.loc[
                filtered_amendments_df["amdt_idx"] == best_matching_doc_amdt_idx, "Sort"
            ].values[0]

            # Set a default for the Commentaires column if it is empty
            amendments_df.loc[amendment_mask, "Sort"] = matching_sort
            amendments_df.loc[amendment_mask, "Commentaires"] = amendments_df.loc[
                amendment_mask, "Commentaires"
            ].apply(lambda x: "" if pd.isna(x) else x)
            # Prepend the Commentaires column with "Attention : Irrecevable en commission"
            current_commentaires = amendments_df.loc[
                amendment_mask, "Commentaires"
            ].values[0]
            amendments_df.loc[amendment_mask, "Commentaires"] = (
                "Attention : Irrecevable en commission"
            )
            if current_commentaires:
                amendments_df.loc[amendment_mask, "Commentaires"] += (
                    f"\n\n{current_commentaires}"
                )

        logging.info(
            f'Added "Attention : Irrecevable en commission" comment to {len(closest_amdts)} amendments'
        )
        end_time = time.time()
        logging.info(
            f"Inadmissible amdts processed in: {end_time - start_time} seconds"
        )

        return amendments_df
