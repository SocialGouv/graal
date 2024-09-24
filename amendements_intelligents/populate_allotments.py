import logging
import logging.config
import os
import time

from amendements_intelligents.allotment.allotment_handler import AllotmentHandler
from amendements_intelligents.utils.amendment_pre_processor import AmendmentPreProcessor

logging.config.fileConfig("logging.conf")


def main():
    start_time = time.time()
    DATA_FOLDER = os.getenv("DATA_FOLDER", "data")
    INPUT_FILE = f"{DATA_FOLDER}/PLFSS_2024.json"
    YEAR = 2024
    OUTPUT_FILE = f"{DATA_FOLDER}/amendments_with_allotments_refactor.xlsx"
    COLUMNS_TO_OUTPUT = [
        "Lecture",
        "Num amdt",
        "Num article",
        "amdt_idx",
        "Allotissement",
        "Corps amdt",
        "Exposé amdt",
    ]

    amendments_df = AmendmentPreProcessor.load_amendments_json(
        input_files=[(INPUT_FILE, YEAR)]
    )
    acronym_mapping = AmendmentPreProcessor.load_acronyms_excel(
        acronym_file=f"{DATA_FOLDER}/acronym_mapping.xlsx"
    )
    original_amendments_df = AllotmentHandler.preprocess_json_amendments(
        amendments_df=amendments_df
    )
    normalized_amdt_df = AllotmentHandler.preprocess_amendments(
        amendments_df=amendments_df,
        acronym_mapping=acronym_mapping,
    )

    allotted_amdt_clusters = AllotmentHandler.get_clusters(
        normalized_amdt_df=normalized_amdt_df
    )

    normalized_amdt_df = AllotmentHandler.filter_amdts_to_keep_one_per_allotment(
        normalized_amdt_df=normalized_amdt_df,
        allotted_amdt_clusters=allotted_amdt_clusters,
    )

    amdt_with_allotments_df = AllotmentHandler.populate(
        original_amendments_df=original_amendments_df,
        pipeline_result_amdt_df=normalized_amdt_df,
        allotted_amdt_clusters=allotted_amdt_clusters,
        columns_to_copy=None,
    )

    amdt_with_allotments_df[COLUMNS_TO_OUTPUT].to_excel(OUTPUT_FILE, index=False)
    logging.info(f"Saved result in {OUTPUT_FILE}\n")

    end_time = time.time()
    execution_time = end_time - start_time
    logging.info(f"Script execution time: {execution_time} seconds")


if __name__ == "__main__":
    main()
