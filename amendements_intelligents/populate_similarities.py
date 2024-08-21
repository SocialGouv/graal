import os
import time

from amendements_intelligents.clustering.similarity_finder import SimilarityFinder
from amendements_intelligents.utils.plfss_amendment_copier import AmendmentCopier
from amendements_intelligents.utils.plfss_pre_processor import PLFSSPreProcessor
from amendements_intelligents.utils.plfss_text_utils import normalize_text

DATA_FOLDER = os.getenv("DATA_FOLDER", "data")
OUTPUT_FILE = (
    f"{DATA_FOLDER}/amendments_with_similarity_2024_with_summary_comparison.xlsx"
)
COLUMNS_TO_OUTPUT = [
    "Num amdt",
    "Lecture",
    "Commentaires",
    "Objet",
    "Objet found",
    "Exposé amdt",
    "Exposé amdt found",
    "Corps amdt",
    "Corps amdt found",
    "Réponse",
    "Sort",
]


def main():
    old_plfss_data_processor = PLFSSPreProcessor()
    old_plfss_data_processor.load_acronyms_excel(f"{DATA_FOLDER}/acronym_mapping.xlsx")
    old_plfss_data_processor.load_plfss_json(
        input_files=[
            (f"{DATA_FOLDER}/PLFSS_2023.json", 2023),
            (f"{DATA_FOLDER}/PLFSS_2022.json", 2022),
            # (f"{DATA_FOLDER}/PLFSS_2021.json", 2021),
        ]
    )
    old_plfss_data_processor.remap_columns_in_json_amendments()
    old_plfss_data_processor.prepare_work_amendments_df()
    old_plfss_data_processor.replace_acronyms(columns_to_normalize=["Exposé amdt"])
    old_plfss_data_processor.remove_empty_rows_for_given_columns(
        columns_to_filter_with=["Exposé amdt", "Corps amdt"]
    )
    old_plfss_data_processor.handle_common_amendment_bodies()
    old_plfss_data_processor.handle_common_amendment_expose()
    old_amendments_df = old_plfss_data_processor.normalize_plfss(
        columns_to_normalize=["Exposé amdt", "Objet"]
    )

    new_plfss_data_processor = PLFSSPreProcessor()
    new_plfss_data_processor.load_acronyms_excel(f"{DATA_FOLDER}/acronym_mapping.xlsx")
    new_plfss_data_processor.load_plfss_json(
        input_files=[(f"{DATA_FOLDER}/PLFSS_2024.json", 2024)]
    )
    new_plfss_data_processor.remap_columns_in_json_amendments()
    new_plfss_data_processor.prepare_work_amendments_df()
    new_plfss_data_processor.replace_acronyms(columns_to_normalize=["Exposé amdt"])
    new_plfss_data_processor.remove_empty_rows_for_given_columns(
        columns_to_filter_with=["Exposé amdt", "Corps amdt"]
    )
    new_plfss_data_processor.handle_common_amendment_bodies()
    new_plfss_data_processor.handle_common_amendment_expose()
    new_amendments_df = new_plfss_data_processor.normalize_plfss(
        columns_to_normalize=["Exposé amdt", "Objet"]
    )

    similarity_evaluator_expose = SimilarityFinder(
        old_amendments_df=old_amendments_df,
        new_amendments_df=new_amendments_df,
        default_threshold_ratio=0.75,
        threshold_ratio_mappings={"amendement redactionnel": 0.85},
    )
    similarity_evaluator_expose.prefilter_similar_docs(
        column_used_for_comparison="Exposé amdt", threshold=0.7
    )
    closest_docs_expose = similarity_evaluator_expose.find_best_matches(
        column_used_for_comparison="Exposé amdt"
    )

    filtered_old_amendments_df = old_amendments_df.copy()
    objet_prefixes_for_removal = (
        normalize_text("amendement rédactionnel"),
        normalize_text("rédactionnel"),
        normalize_text("amendement de suppression"),
        normalize_text("supprimer l'article"),
    )
    filtered_old_amendments_df = filtered_old_amendments_df[
        ~filtered_old_amendments_df["Objet"].str.startswith(objet_prefixes_for_removal)
    ]

    similarity_evaluator_object = SimilarityFinder(
        old_amendments_df=filtered_old_amendments_df,
        new_amendments_df=new_amendments_df,
        default_threshold_ratio=0.95,
    )
    similarity_evaluator_object.prefilter_similar_docs(
        column_used_for_comparison="Objet", threshold=0.95
    )
    closest_docs_object = similarity_evaluator_object.find_best_matches(
        column_used_for_comparison="Objet"
    )

    # Merge closest_docs_expose and closest_docs_object together while keeping the best match if a conflict occurs
    closest_docs = {}
    for doc_id, doc_info in closest_docs_expose.items():
        if doc_id in closest_docs_object:
            if (
                doc_info["similarity_ratio"]
                > closest_docs_object[doc_id]["similarity_ratio"]
            ):
                closest_docs[doc_id] = doc_info
            else:
                closest_docs[doc_id] = closest_docs_object[doc_id]
        else:
            closest_docs[doc_id] = doc_info

    for doc_id, doc_info in closest_docs_object.items():
        if doc_id not in closest_docs:
            closest_docs[doc_id] = doc_info

    print(f"Total number of matches after merge: {len(closest_docs)}")

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
    start_time = time.time()
    main()
    end_time = time.time()
    print(f"Execution time: {end_time - start_time} seconds")
