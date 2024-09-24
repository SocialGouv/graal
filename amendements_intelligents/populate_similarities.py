import logging
import logging.config
import os
import time

import pandas as pd

from amendements_intelligents.clustering.similarity_finder import SimilarityFinder
from amendements_intelligents.utils.amendment_copier import AmendmentCopier
from amendements_intelligents.utils.amendment_pre_processor import AmendmentPreProcessor
from amendements_intelligents.utils.text_utils import normalize_text

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
            columns_to_normalize=["Exposé amdt", "Objet amdt"],
        )

        return amendments_df

    @staticmethod
    def populate(
        preprocessed_old_amendments_df: pd.DataFrame,
        preprocessed_new_amendments_df: pd.DataFrame,
        original_new_amendments_df: pd.DataFrame,
    ) -> pd.DataFrame:
        # Perform similarity evaluation for Exposé amdt
        similarity_evaluator_expose = SimilarityFinder(
            old_amendments_df=preprocessed_old_amendments_df,
            new_amendments_df=preprocessed_new_amendments_df,
            default_threshold_ratio=0.75,
            threshold_ratio_mappings={"amendement redactionnel": 0.9},
        )
        similarity_evaluator_expose.prefilter_similar_docs(
            column_used_for_similarity="Exposé amdt", threshold=0.7
        )
        closest_amdts_expose = similarity_evaluator_expose.find_best_matches(
            column_used_for_similarity="Exposé amdt"
        )

        # For object comparison, we remove the redactionnel and suppression amendments
        filtered_old_amendments_df = preprocessed_old_amendments_df.copy()
        objet_prefixes_for_removal = (
            normalize_text("amendement rédactionnel"),
            normalize_text("rédactionnel"),
            normalize_text("amendement de suppression"),
            normalize_text("supprimer l'article"),
            normalize_text("supprimer cet article"),
        )
        filtered_old_amendments_df = filtered_old_amendments_df[
            ~filtered_old_amendments_df["Objet amdt"].str.startswith(
                objet_prefixes_for_removal
            )
        ]

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
    OUTPUT_FILE = (
        f"{DATA_FOLDER}/amendments_with_similarity_2024_with_summary_comparison.xlsx"
    )
    COLUMNS_TO_OUTPUT = [
        "Num amdt",
        "Lecture",
        "Commentaires",
        "Objet amdt",
        "Exposé amdt",
        "Corps amdt",
        "Réponse",
        "Sort",
    ]
    acronym_mapping = AmendmentPreProcessor.load_acronyms_excel(
        f"{DATA_FOLDER}/acronym_mapping.xlsx"
    )
    old_amendments_df = AmendmentPreProcessor.load_amendments_json(
        input_files=[
            (f"{DATA_FOLDER}/PLFSS_2023.json", 2023),
            (f"{DATA_FOLDER}/PLFSS_2022.json", 2022),
            (f"{DATA_FOLDER}/PLFSS_2021.json", 2021),
        ]
    )
    new_amendments_df = AmendmentPreProcessor.load_amendments_json(
        input_files=[(f"{DATA_FOLDER}/PLFSS_2024.json", 2024)]
    )
    original_new_amendments_df = new_amendments_df.copy()
    original_new_amendments_df = AmendmentPreProcessor.remap_columns_in_json_amendments(
        amendments_df=original_new_amendments_df
    )
    original_new_amendments_df = AmendmentPreProcessor.clear_columns_to_be_overridden(
        amendments_df=original_new_amendments_df, columns_to_clear=["Réponse", "Sort"]
    )

    old_amendments_df = SimilarityHandler.preprocess_for_similarity(
        amendments_df=old_amendments_df, acronym_mapping=acronym_mapping
    )

    new_amendments_df = SimilarityHandler.preprocess_for_similarity(
        amendments_df=new_amendments_df, acronym_mapping=acronym_mapping
    )
    new_amendments_df = AmendmentPreProcessor.clear_columns_to_be_overridden(
        amendments_df=new_amendments_df, columns_to_clear=["Réponse", "Sort"]
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
