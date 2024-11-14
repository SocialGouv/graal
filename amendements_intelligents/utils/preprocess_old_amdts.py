"""
This module preprocesses old amendments for similarity search.

It includes functions to load and preprocess amendments from JSON and Excel files,
process the amendments to filter and cluster them (in order to remove duplicates), and save the processed amendments
to a file. These will then be used to populate similarities between old and new amendments in the amendement processing pipeline.
"""

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
from amendements_intelligents.clustering.similarity_handler import SimilarityHandler
from amendements_intelligents.types import IntIndex
from amendements_intelligents.utils.amendment_pre_processor import AmendmentPreProcessor

logging.config.fileConfig("logging.conf")

DATA_FOLDER = os.getenv("DATA_FOLDER", "data")
OUTPUT_FILE = f"{DATA_FOLDER}/preprocessed/pre_processed_old_amdts.pkl"
ATTRIBUTION_MAPPINGS_FILE = f"{DATA_FOLDER}/mappings_attributions_nov_14.xlsx"

PLFSS_FILE_CONFIG_JSON = {
    f"{DATA_FOLDER}/exports_lectures/PLFSS 2021 JSON/lecture-senat-2020-2021-101-PO78718.json": {
        "default_timestamp": int(datetime(2021, month=7, day=1).timestamp()),
        "origin_project": "PLFSS",
    },
    f"{DATA_FOLDER}/exports_lectures/PLFSS 2021 JSON/lecture-an-15-3551-PO717460.json": {
        "default_timestamp": int(datetime(2021, month=7, day=1).timestamp()),
        "origin_project": "PLFSS",
    },
    f"{DATA_FOLDER}/exports_lectures/PLFSS 2021 JSON/lecture-an-15-3397-PO717460.json": {
        "default_timestamp": int(datetime(2021, month=7, day=1).timestamp()),
        "origin_project": "PLFSS",
    },
    f"{DATA_FOLDER}/exports_lectures/PLFSS 2021 JSON/lecture-an-15-3397-PO420120.json": {
        "default_timestamp": int(datetime(2021, month=7, day=1).timestamp()),
        "origin_project": "PLFSS",
    },
    f"{DATA_FOLDER}/exports_lectures/PLFSS 2022 - JSON/lecture-senat-2021-2022-118-PO78718.json": {
        "default_timestamp": int(datetime(2022, month=7, day=1).timestamp()),
        "origin_project": "PLFSS",
    },
    f"{DATA_FOLDER}/exports_lectures/PLFSS 2022 - JSON/lecture-senat-2021-2022-189-PO78718.json": {
        "default_timestamp": int(datetime(2022, month=7, day=1).timestamp()),
        "origin_project": "PLFSS",
    },
    f"{DATA_FOLDER}/exports_lectures/PLFSS 2022 - JSON/lecture-an-15-4685-PO717460.json": {
        "default_timestamp": int(datetime(2022, month=7, day=1).timestamp()),
        "origin_project": "PLFSS",
    },
    f"{DATA_FOLDER}/exports_lectures/PLFSS 2022 - JSON/lecture-an-15-4523-PO717460.json": {
        "default_timestamp": int(datetime(2022, month=7, day=1).timestamp()),
        "origin_project": "PLFSS",
    },
    f"{DATA_FOLDER}/exports_lectures/PLFSS 2023/lecture-senat-2022-2023-96-PO78718.json": {
        "default_timestamp": int(datetime(2023, month=7, day=1).timestamp()),
        "origin_project": "PLFSS",
    },
    f"{DATA_FOLDER}/exports_lectures/PLFSS 2023/lecture-an-16-274-PO791932.json": {
        "default_timestamp": int(datetime(2023, month=7, day=1).timestamp()),
        "origin_project": "PLFSS",
    },
    f"{DATA_FOLDER}/exports_lectures/PLFSS 2023/lecture-an-16-274-PO420120.json": {
        "default_timestamp": int(datetime(2023, month=7, day=1).timestamp()),
        "origin_project": "PLFSS",
    },
    f"{DATA_FOLDER}/exports_lectures/PLFSS 2023/lecture-an-16-1682-PO791932 (2).json": {
        "default_timestamp": int(datetime(2023, month=7, day=1).timestamp()),
        "origin_project": "PLFSS",
    },
    f"{DATA_FOLDER}/exports_lectures/PLFSS 2023/lecture-an-16-480-PO791932.json": {
        "default_timestamp": int(datetime(2023, month=7, day=1).timestamp()),
        "origin_project": "PLFSS",
    },
    f"{DATA_FOLDER}/exports_lectures/Export PLFSS 2024/JSON/lecture-an-16-1682-PO420120.json": {
        "default_timestamp": int(datetime(2024, month=7, day=1).timestamp()),
        "origin_project": "PLFSS",
    },
    f"{DATA_FOLDER}/exports_lectures/Export PLFSS 2024/JSON/lecture-an-16-1875-PO791932.json": {
        "default_timestamp": int(datetime(2024, month=7, day=1).timestamp()),
        "origin_project": "PLFSS",
    },
    f"{DATA_FOLDER}/exports_lectures/Export PLFSS 2024/JSON/lecture-senat-2023-2024-77-PO78718.json": {
        "default_timestamp": int(datetime(2024, month=7, day=1).timestamp()),
        "origin_project": "PLFSS",
    },
}

PLACSS_FILE_CONFIG_JSON = {
    f"{DATA_FOLDER}/exports_lectures/PLACSS 22/AN Séance 1ère lecture/lecture-an-16-1268-PO791932.json": {
        "default_timestamp": int(datetime(2022, month=7, day=1).timestamp()),
        "origin_project": "PLACSS",
    },
    f"{DATA_FOLDER}/exports_lectures/PLACSS 22/Sénat Séance 1ère lecture/lecture-senat-2022-2023-705-PO78718.json": {
        "default_timestamp": int(datetime(2022, month=7, day=1).timestamp()),
        "origin_project": "PLACSS",
    },
}

LFRSS_FILE_CONFIG_JSON = {
    f"{DATA_FOLDER}/exports_lectures/PPL LIOT 2023 abrogation réforme des retraites/Séance AN/lecture-an-16-1299-PO791932.json": {
        "default_timestamp": int(datetime(2023, month=7, day=1).timestamp()),
        "origin_project": "LFRSS",
    },
    f"{DATA_FOLDER}/exports_lectures/LFRSS 2023/lecture-an-16-760-PO791932.json": {
        "default_timestamp": int(datetime(2023, month=7, day=1).timestamp()),
        "origin_project": "LFRSS",
    },
    f"{DATA_FOLDER}/exports_lectures/LFRSS 2023/lecture-an-16-760-PO420120.json": {
        "default_timestamp": int(datetime(2023, month=7, day=1).timestamp()),
        "origin_project": "LFRSS",
    },
    f"{DATA_FOLDER}/exports_lectures/LFRSS 2023/lecture-senat-2022-2023-368-PO78718.json": {
        "default_timestamp": int(datetime(2023, month=7, day=1).timestamp()),
        "origin_project": "LFRSS",
    },
}

ALL_INPUT_FILE_CONFIGS_JSON = {
    **PLFSS_FILE_CONFIG_JSON,
    **PLACSS_FILE_CONFIG_JSON,
    **LFRSS_FILE_CONFIG_JSON,
}

PLFSS_FILE_CONFIG_EXCEL = {
    f"{DATA_FOLDER}/exports_lectures/PLFSS 2025/lecture_AN_avec_toutes_reponses.xlsx": {
        "default_timestamp": int(datetime(2024, month=10, day=17).timestamp()),
        "origin_project": "PLFSS",
    },
}
ALL_INPUT_FILE_CONFIGS_EXCEL = {**PLFSS_FILE_CONFIG_EXCEL}


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
    file_configs_json: dict[FilePath, Any],
    file_configs_excel: dict[FilePath, Any],
    acronym_mapping: pd.DataFrame,
) -> pd.DataFrame:
    amendments_df_json = AmendmentPreProcessor.load_amendments_json(
        list(file_configs_json.keys()), file_configs_json
    )
    amendments_df_json = SimilarityHandler.preprocess_for_similarity(
        amendments_df_json, acronym_mapping
    )
    amendments_df_excel = AmendmentPreProcessor.load_amendments_excel(
        list(file_configs_excel.keys()), file_configs_excel
    )
    amendments_df_excel = SimilarityHandler.preprocess_for_similarity(
        amendments_df_excel, acronym_mapping
    )
    amendments_df = AmendmentPreProcessor.concatenate_dataframes(
        amendments_df_json, amendments_df_excel
    )
    return amendments_df


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
    logging.info(f"Dumped pre-processed old amendments in {output_file}")


def main():
    attribution_mappings_excel = pd.read_excel(
        ATTRIBUTION_MAPPINGS_FILE, sheet_name=None
    )
    acronym_mapping = AmendmentPreProcessor.load_acronyms(
        attribution_mappings_excel["Acronymes"]
    )
    amendments_df = load_and_preprocess_amendments(
        ALL_INPUT_FILE_CONFIGS_JSON,
        ALL_INPUT_FILE_CONFIGS_EXCEL,
        acronym_mapping=acronym_mapping,
    )
    processed_df = process_amendments(amendments_df)
    logging.info(
        f"Number of old amendments available for similarity search: {len(processed_df)}"
    )
    save_processed_amendments(processed_df, OUTPUT_FILE)


if __name__ == "__main__":
    start_time = time.time()
    main()
    end_time = time.time()
    logging.info(f"Total execution time: {end_time - start_time:.2f} seconds")
