import os

from amendements_intelligents.clustering.similarity_finder import SimilarityFinder
from amendements_intelligents.utils.plfss_amendment_copier import (
    AmendmentCopier,
)
from amendements_intelligents.utils.plfss_pre_processor import PLFSSPreProcessor

DATA_FOLDER = os.getenv("DATA_FOLDER", "data")
OLD_PLFSS_YEAR = 2023
NEW_PLFSS_YEAR = 2024
INPUT_FILE_OLD_PLFSS = f"{DATA_FOLDER}/PLFSS_{OLD_PLFSS_YEAR}.json"
INPUT_FILE_NEW_PLFSS = f"{DATA_FOLDER}/PLFSS_{NEW_PLFSS_YEAR}.json"
OUTPUT_FILE = f"{DATA_FOLDER}/amendments_with_similarity_{NEW_PLFSS_YEAR}.xlsx"
COLUMNS_TO_OUTPUT = [
    "Num amdt",
    "Lecture",
    "Num article",
    "Sort",
    "Commentaires",
    "Réponse",
    "Exposé amdt",
    "Exposé amdt found",
    "Corps amdt",
    "Corps amdt found",
]


def main():
    old_plfss_data_processor = PLFSSPreProcessor()
    old_plfss_data_processor.load_plfss(input_file=INPUT_FILE_OLD_PLFSS)
    old_plfss_data_processor.clean_up_original_amendments()
    old_plfss_data_processor.prepare_work_amendments_df()
    old_plfss_data_processor.remove_empty_rows_for_given_columns(
        columns_to_filter_with=["Exposé amdt", "Corps amdt"]
    )
    old_plfss_data_processor.handle_common_amendment_bodies()
    old_plfss_data_processor.handle_common_amendment_expose()
    old_amendments_df = old_plfss_data_processor.normalize_plfss(
        columns_to_normalize=["Exposé amdt"]
    )
    old_amendments_df["Year"] = OLD_PLFSS_YEAR

    new_plfss_data_processor = PLFSSPreProcessor()
    new_plfss_data_processor.load_plfss(input_file=INPUT_FILE_NEW_PLFSS)
    new_plfss_data_processor.clean_up_original_amendments()
    new_plfss_data_processor.prepare_work_amendments_df()
    new_plfss_data_processor.remove_empty_rows_for_given_columns(
        columns_to_filter_with=["Exposé amdt", "Corps amdt"]
    )
    new_plfss_data_processor.handle_common_amendment_bodies()
    new_plfss_data_processor.handle_common_amendment_expose()
    new_amendments_df = new_plfss_data_processor.normalize_plfss(
        columns_to_normalize=["Exposé amdt"]
    )

    new_amendments_df["Year"] = NEW_PLFSS_YEAR

    similarity_evaluator = SimilarityFinder(
        old_amendments_df=old_amendments_df,
        new_amendments_df=new_amendments_df,
    )
    similarity_evaluator.prefilter_similar_docs(
        column_used_for_comparison="Exposé amdt", threshold=0.7
    )
    closest_docs = similarity_evaluator.find_best_matches(
        column_used_for_comparison="Exposé amdt", threshold_ratio=0.75
    )

    amendment_copier = AmendmentCopier(
        new_amendments_df=new_amendments_df,
        old_amendments_df=old_amendments_df,
        closest_docs=closest_docs,
    )
    new_amendments_with_copies_df = amendment_copier.copy_matches_to_plfss_df(
        target_df=new_plfss_data_processor.original_amendments_df
    )

    new_amendments_with_copies_df[COLUMNS_TO_OUTPUT].to_excel(OUTPUT_FILE, index=False)
    print(f"Saved result in {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
