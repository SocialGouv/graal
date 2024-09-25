import logging
import logging.config
import os
import pickle
import time

from amendements_intelligents.populate_similarities import SimilarityHandler
from amendements_intelligents.utils.amendment_pre_processor import AmendmentPreProcessor

logging.config.fileConfig("logging.conf")


def main():
    DATA_FOLDER = os.getenv("DATA_FOLDER")
    OUTPUT_FILE = f"{DATA_FOLDER}/pre_processed_old_amdts.pkl"
    ACRONYM_FILE = f"{DATA_FOLDER}/acronym_mapping.xlsx"

    PLFSS_FILES = [
        (
            f"{DATA_FOLDER}/exports_lectures/PLFSS 2021 JSON/lecture-senat-2020-2021-101-PO78718.json",
            2021,
        ),
        (
            f"{DATA_FOLDER}/exports_lectures/PLFSS 2021 JSON/lecture-an-15-3551-PO717460.json",
            2021,
        ),
        (
            f"{DATA_FOLDER}/exports_lectures/PLFSS 2021 JSON/lecture-an-15-3397-PO717460.json",
            2021,
        ),
        (
            f"{DATA_FOLDER}/exports_lectures/PLFSS 2021 JSON/lecture-an-15-3397-PO420120.json",
            2021,
        ),
        (
            f"{DATA_FOLDER}/exports_lectures/PLFSS 2022 - JSON/lecture-senat-2021-2022-118-PO78718.json",
            2022,
        ),
        (
            f"{DATA_FOLDER}/exports_lectures/PLFSS 2022 - JSON/lecture-senat-2021-2022-189-PO78718.json",
            2022,
        ),
        (
            f"{DATA_FOLDER}/exports_lectures/PLFSS 2022 - JSON/lecture-an-15-4685-PO717460.json",
            2022,
        ),
        (
            f"{DATA_FOLDER}/exports_lectures/PLFSS 2022 - JSON/lecture-an-15-4523-PO717460.json",
            2022,
        ),
        (
            f"{DATA_FOLDER}/exports_lectures/PLFSS 2022 - JSON/lecture-an-15-698-PO717460.json",
            2022,
        ),
        (
            f"{DATA_FOLDER}/exports_lectures/PLFSS 2023/lecture-senat-2022-2023-96-PO78718.json",
            2023,
        ),
        (
            f"{DATA_FOLDER}/exports_lectures/PLFSS 2023/lecture-an-16-274-PO791932.json",
            2023,
        ),
        (
            f"{DATA_FOLDER}/exports_lectures/PLFSS 2023/lecture-an-16-274-PO420120.json",
            2023,
        ),
        (
            f"{DATA_FOLDER}/exports_lectures/PLFSS 2023/lecture-an-16-1682-PO791932 (2).json",
            2023,
        ),
        (
            f"{DATA_FOLDER}/exports_lectures/PLFSS 2023/lecture-an-16-480-PO791932.json",
            2023,
        ),
    ]

    PLACSS_FILES = [
        (
            f"{DATA_FOLDER}/exports_lectures/PLACSS 22/AN Séance 1ère lecture/lecture-an-16-1268-PO791932.json",
            2022,
        ),
        (
            f"{DATA_FOLDER}/exports_lectures/PLACSS 22/Sénat Séance 1ère lecture/lecture-senat-2022-2023-705-PO78718.json",
            2022,
        ),
    ]

    LFRSS_FILES = [
        (
            f"{DATA_FOLDER}/exports_lectures/PPL LIOT 2023 abrogation réforme des retraites/Séance AN/lecture-an-16-1299-PO791932.json",
            2023,
        ),
        (
            f"{DATA_FOLDER}/exports_lectures/LFRSS 2023/lecture-an-16-760-PO791932.json",
            2023,
        ),
        (
            f"{DATA_FOLDER}/exports_lectures/LFRSS 2023/lecture-an-16-760-PO420120.json",
            2023,
        ),
        (
            f"{DATA_FOLDER}/exports_lectures/LFRSS 2023/lecture-senat-2022-2023-368-PO78718.json",
            2023,
        ),
    ]

    SIMILARITY_INPUT_FILES = PLFSS_FILES + PLACSS_FILES + LFRSS_FILES

    acronym_mapping = AmendmentPreProcessor.load_acronyms_excel(
        acronym_file=ACRONYM_FILE
    )
    old_amendments_df = AmendmentPreProcessor.load_amendments_json(
        input_files=SIMILARITY_INPUT_FILES
    )
    old_amendments_df = SimilarityHandler.preprocess_for_similarity(
        amendments_df=old_amendments_df, acronym_mapping=acronym_mapping
    )
    with open(OUTPUT_FILE, "wb") as f:
        pickle.dump(old_amendments_df, f)
        logging.info(f"Dumped pre-processed old amendments in {OUTPUT_FILE}")


if __name__ == "__main__":
    start_time = time.time()
    main()
    end_time = time.time()
    logging.info(f"Total execution time: {end_time - start_time} seconds")
