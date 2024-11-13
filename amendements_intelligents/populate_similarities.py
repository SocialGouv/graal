import logging
import logging.config
import os
import time

import pandas as pd

from amendements_intelligents.clustering.similarity_finder import SimilarityFinder
from amendements_intelligents.utils.amendment_copier import AmendmentCopier
from amendements_intelligents.utils.amendment_pre_processor import AmendmentPreProcessor

logging.config.fileConfig("logging.conf")


class SimilarityHandler:
    @staticmethod
    def preprocess_for_similarity(
        amendments_df: pd.DataFrame, acronym_mapping: dict[str, str]
    ) -> pd.DataFrame:
        amendments_df = AmendmentPreProcessor.remap_columns_in_json_amendments(
            amendments_df=amendments_df
        )
        amendments_df = AmendmentPreProcessor.replace_acronyms(
            amendments_df=amendments_df,
            acronym_mapping=acronym_mapping,
            columns_to_normalize=["Exposé amdt"],
        )
        amendments_df = AmendmentPreProcessor.remove_empty_rows_for_given_columns(
            amendments_df=amendments_df,
            columns_to_filter_with=["Exposé amdt", "Corps amdt"],
        )
        amendments_df = AmendmentPreProcessor.handle_common_amendment_bodies(
            amendments_df=amendments_df
        )
        amendments_df = AmendmentPreProcessor.handle_common_amendment_expose(
            amendments_df=amendments_df
        )
        amendments_df = AmendmentPreProcessor.normalize_amendments(
            amendments_df=amendments_df,
            columns_to_normalize=["Exposé amdt"],
        )

        return amendments_df

    @staticmethod
    def populate(
        preprocessed_old_amendments_df: pd.DataFrame,
        preprocessed_new_amendments_df: pd.DataFrame,
        original_new_amendments_df: pd.DataFrame,
        clustering_similarity_threshold: float = 0.4,
        exact_match_similarity_threshold: float = 0.4,
    ) -> pd.DataFrame:
        # Perform similarity evaluation for Exposé amdt
        similarity_evaluator_expose = SimilarityFinder(
            old_amendments_df=preprocessed_old_amendments_df,
            new_amendments_df=preprocessed_new_amendments_df,
            similarity_threshold_overrides={"amendement redactionnel": 0.95},
        )
        similarity_evaluator_expose.prefilter_similar_docs(
            column_used_for_similarity="Exposé amdt",
            clustering_similarity_threshold=clustering_similarity_threshold,
        )
        closest_amdts_expose = similarity_evaluator_expose.find_best_matches(
            column_used_for_similarity="Exposé amdt",
            exact_match_similarity_threshold=exact_match_similarity_threshold,
        )

        # Copy matched amendments to new_amendments_df
        amendment_copier = AmendmentCopier(
            new_amendments_df=preprocessed_new_amendments_df,
            old_amendments_df=preprocessed_old_amendments_df,
            closest_amdts=closest_amdts_expose,
        )
        new_amendments_with_copies_df = amendment_copier.copy_matches_to_amendments_df(
            target_df=original_new_amendments_df
        )

        return new_amendments_with_copies_df


def main():
    DATA_FOLDER = os.getenv("DATA_FOLDER", "data")
    PRE_PROCESSED_OLD_AMENDMENTS_FILE = f"{DATA_FOLDER}/pre_processed_old_amdts.pkl"
    INPUT_FILE = f"{DATA_FOLDER}/input_plfss/lecture-an-17-325-PO420120.json"
    OUTPUT_FILE = f"{DATA_FOLDER}/test_recurrence_similarité.xlsx"
    COLUMNS_TO_OUTPUT = [
        "Num amdt",
        "Lecture",
        "Commentaires",
        "Réponse",
        "Sort",
        "Objet amdt",
        "Exposé amdt",
        "Corps amdt",
    ]
    acronym_mapping = AmendmentPreProcessor.load_acronyms_excel(
        f"{DATA_FOLDER}/acronym_mapping.xlsx"
    )
    old_amendments_df = pd.read_pickle(PRE_PROCESSED_OLD_AMENDMENTS_FILE)

    logging.info(f"Loaded old amendments from: {PRE_PROCESSED_OLD_AMENDMENTS_FILE}")
    new_amendments_df = AmendmentPreProcessor.load_amendments_json(
        input_files=[INPUT_FILE]
    )
    original_new_amendments_df = new_amendments_df.copy()
    original_new_amendments_df = AmendmentPreProcessor.remap_columns_in_json_amendments(
        amendments_df=original_new_amendments_df
    )
    original_new_amendments_df = AmendmentPreProcessor.clear_columns_to_be_overridden(
        amendments_df=original_new_amendments_df,
        columns_to_clear=["Réponse", "Sort", "Commentaires"],
    )

    old_amendments_df = SimilarityHandler.preprocess_for_similarity(
        amendments_df=old_amendments_df, acronym_mapping=acronym_mapping
    )

    new_amendments_df = SimilarityHandler.preprocess_for_similarity(
        amendments_df=new_amendments_df, acronym_mapping=acronym_mapping
    )
    new_amendments_df = AmendmentPreProcessor.clear_columns_to_be_overridden(
        amendments_df=new_amendments_df,
        columns_to_clear=["Réponse", "Sort", "Commentaires"],
    )

    new_amendments_with_copies_df = SimilarityHandler.populate(
        preprocessed_old_amendments_df=old_amendments_df,
        preprocessed_new_amendments_df=new_amendments_df,
        original_new_amendments_df=original_new_amendments_df,
    )

    new_amendments_with_copies_df[COLUMNS_TO_OUTPUT].to_excel(OUTPUT_FILE, index=False)
    logging.info(f"Saved result in {OUTPUT_FILE}")


if __name__ == "__main__":
    start_time = time.time()
    main()
    end_time = time.time()
    logging.info(f"Execution time: {end_time - start_time} seconds")
