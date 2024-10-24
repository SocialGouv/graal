import logging
import logging.config
import os
import pickle
import time
from datetime import datetime
from typing import Any

import pandas as pd
from pydantic import FilePath

from amendements_intelligents.allotment.allotment_handler import AllotmentHandler
from amendements_intelligents.populate_similarities import SimilarityHandler
from amendements_intelligents.types import IntIndex
from amendements_intelligents.utils.amendment_pre_processor import AmendmentPreProcessor

logging.config.fileConfig("logging.conf")
logger = logging.getLogger(__name__)

DATA_FOLDER = os.getenv("DATA_FOLDER", "data")
OUTPUT_FILE = f"{DATA_FOLDER}/preprocessed/pre_processed_old_amdts.pkl"
ACRONYM_FILE = f"{DATA_FOLDER}/acronym_mapping.xlsx"

PLFSS_FILE_CONFIG = {
    f"{DATA_FOLDER}/exports_lectures/PLFSS 2021 JSON/lecture-senat-2020-2021-101-PO78718.json": {
        "default_timestamp": int(datetime(2021, 7, 1).timestamp())
    },
    f"{DATA_FOLDER}/exports_lectures/PLFSS 2021 JSON/lecture-an-15-3551-PO717460.json": {
        "default_timestamp": int(datetime(2021, 7, 1).timestamp())
    },
    f"{DATA_FOLDER}/exports_lectures/PLFSS 2021 JSON/lecture-an-15-3397-PO717460.json": {
        "default_timestamp": int(datetime(2021, 7, 1).timestamp())
    },
    f"{DATA_FOLDER}/exports_lectures/PLFSS 2021 JSON/lecture-an-15-3397-PO420120.json": {
        "default_timestamp": int(datetime(2021, 7, 1).timestamp())
    },
    f"{DATA_FOLDER}/exports_lectures/PLFSS 2022 - JSON/lecture-senat-2021-2022-118-PO78718.json": {
        "default_timestamp": int(datetime(2022, 7, 1).timestamp())
    },
    f"{DATA_FOLDER}/exports_lectures/PLFSS 2022 - JSON/lecture-senat-2021-2022-189-PO78718.json": {
        "default_timestamp": int(datetime(2022, 7, 1).timestamp())
    },
    f"{DATA_FOLDER}/exports_lectures/PLFSS 2022 - JSON/lecture-an-15-4685-PO717460.json": {
        "default_timestamp": int(datetime(2022, 7, 1).timestamp())
    },
    f"{DATA_FOLDER}/exports_lectures/PLFSS 2022 - JSON/lecture-an-15-4523-PO717460.json": {
        "default_timestamp": int(datetime(2022, 7, 1).timestamp())
    },
    f"{DATA_FOLDER}/exports_lectures/PLFSS 2023/lecture-senat-2022-2023-96-PO78718.json": {
        "default_timestamp": int(datetime(2023, 7, 1).timestamp())
    },
    f"{DATA_FOLDER}/exports_lectures/PLFSS 2023/lecture-an-16-274-PO791932.json": {
        "default_timestamp": int(datetime(2023, 7, 1).timestamp())
    },
    f"{DATA_FOLDER}/exports_lectures/PLFSS 2023/lecture-an-16-274-PO420120.json": {
        "default_timestamp": int(datetime(2023, 7, 1).timestamp())
    },
    f"{DATA_FOLDER}/exports_lectures/PLFSS 2023/lecture-an-16-1682-PO791932 (2).json": {
        "default_timestamp": int(datetime(2023, 7, 1).timestamp())
    },
    f"{DATA_FOLDER}/exports_lectures/PLFSS 2023/lecture-an-16-480-PO791932.json": {
        "default_timestamp": int(datetime(2023, 7, 1).timestamp())
    },
    f"{DATA_FOLDER}/exports_lectures/Export PLFSS 2024/JSON/lecture-an-16-1682-PO420120.json": {
        "default_timestamp": int(datetime(2024, 7, 1).timestamp())
    },
    f"{DATA_FOLDER}/exports_lectures/Export PLFSS 2024/JSON/lecture-an-16-1875-PO791932.json": {
        "default_timestamp": int(datetime(2024, 7, 1).timestamp())
    },
    f"{DATA_FOLDER}/exports_lectures/Export PLFSS 2024/JSON/lecture-senat-2023-2024-77-PO78718.json": {
        "default_timestamp": int(datetime(2024, 7, 1).timestamp())
    },
}

PLACSS_FILE_CONFIG = {
    f"{DATA_FOLDER}/exports_lectures/PLACSS 22/AN Séance 1ère lecture/lecture-an-16-1268-PO791932.json": {
        "default_timestamp": int(datetime(2022, 7, 1).timestamp())
    },
    f"{DATA_FOLDER}/exports_lectures/PLACSS 22/Sénat Séance 1ère lecture/lecture-senat-2022-2023-705-PO78718.json": {
        "default_timestamp": int(datetime(2022, 7, 1).timestamp())
    },
}

LFRSS_FILE_CONFIG = {
    f"{DATA_FOLDER}/exports_lectures/PPL LIOT 2023 abrogation réforme des retraites/Séance AN/lecture-an-16-1299-PO791932.json": {
        "default_timestamp": int(datetime(2023, 7, 1).timestamp())
    },
    f"{DATA_FOLDER}/exports_lectures/LFRSS 2023/lecture-an-16-760-PO791932.json": {
        "default_timestamp": int(datetime(2023, 7, 1).timestamp())
    },
    f"{DATA_FOLDER}/exports_lectures/LFRSS 2023/lecture-an-16-760-PO420120.json": {
        "default_timestamp": int(datetime(2023, 7, 1).timestamp())
    },
    f"{DATA_FOLDER}/exports_lectures/LFRSS 2023/lecture-senat-2022-2023-368-PO78718.json": {
        "default_timestamp": int(datetime(2023, 7, 1).timestamp())
    },
}

ALL_INPUT_FILE_CONFIGS = {
    **PLFSS_FILE_CONFIG,
    **PLACSS_FILE_CONFIG,
    **LFRSS_FILE_CONFIG,
}


def remove_oldest_and_without_response(
    df: pd.DataFrame, cluster: list[IntIndex]
) -> list[IntIndex]:
    filtered_df = df[df["amdt_idx"].isin(cluster)].sort_values(
        by=["timestamp", "Réponse"],
        ascending=[False, False],
        key=lambda x: x if x.name != "Réponse" else x.str.len(),
    )
    return filtered_df["amdt_idx"].tolist()[1:]


def load_and_preprocess_amendments(
    file_configs: dict[FilePath, Any],
    acronym_file: FilePath,
) -> pd.DataFrame:
    input_files = list(file_configs.keys())
    acronym_mapping = AmendmentPreProcessor.load_acronyms_excel(acronym_file)
    amendments_df = AmendmentPreProcessor.load_amendments_json(
        input_files, file_configs
    )
    return SimilarityHandler.preprocess_for_similarity(amendments_df, acronym_mapping)


def process_amendments(amendments_df: pd.DataFrame) -> pd.DataFrame:
    allotted_amdt_clusters = AllotmentHandler.get_clusters(amendments_df)
    return AllotmentHandler.filter_amdts_to_keep_one_per_allotment(
        normalized_amdt_df=amendments_df,
        allotted_amdt_clusters=allotted_amdt_clusters,
        removal_strategy_func=remove_oldest_and_without_response,
    )


def save_processed_amendments(df: pd.DataFrame, output_file: str):
    with open(output_file, "wb") as f:
        pickle.dump(df, f)
    logger.info(f"Dumped pre-processed old amendments in {output_file}")


def main():
    amendments_df = load_and_preprocess_amendments(ALL_INPUT_FILE_CONFIGS, ACRONYM_FILE)
    processed_df = process_amendments(amendments_df)
    save_processed_amendments(processed_df, OUTPUT_FILE)


if __name__ == "__main__":
    start_time = time.time()
    main()
    end_time = time.time()
    logger.info(f"Total execution time: {end_time - start_time:.2f} seconds")
