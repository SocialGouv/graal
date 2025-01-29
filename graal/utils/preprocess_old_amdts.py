"""
This module preprocesses old amendments for similarity search.

It includes functions to load and preprocess amendments from JSON and Excel files,
process the amendments to filter and cluster them (in order to remove duplicates), and save the processed amendments
to a file. These will then be used to populate similarities between old and new amendments in the amendement processing pipeline.
"""

import logging
import logging.config
import os
import pickle  # nosec
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from graal.allotment.allotment_handler import AllotmentHandler
from graal.clustering.similarity_handler import SimilarityHandler
from graal.custom_types import Acronym, InputFileConfig, IntIndex, Seconds
from graal.utils.amendment_pre_processor import AmendmentPreProcessor

logging.config.fileConfig("logging.conf")

DATA_FOLDER = os.getenv("DATA_FOLDER", "data")
OUTPUT_FILE = Path(f"{DATA_FOLDER}/preprocessed/pre_processed_old_amdts.pkl")
ATTRIBUTION_MAPPINGS_FILE = Path(f"{DATA_FOLDER}/mappings_attributions_nov_14.xlsx")

ONE_YEAR_IN_SECONDS: Seconds = 365 * 24 * 60 * 60

PLFSS_FILE_CONFIG_JSON: dict[Path, InputFileConfig] = {
    Path(
        f"{DATA_FOLDER}/exports_lectures/PLFSS 2021 JSON/lecture-senat-2020-2021-101-PO78718.json"
    ): {
        "default_processing_timestamp": int(datetime(2021, month=7, day=1).timestamp()),
        "origin_project": "PLFSS 2022",
    },
    Path(
        f"{DATA_FOLDER}/exports_lectures/PLFSS 2021 JSON/lecture-an-15-3551-PO717460.json"
    ): {
        "default_processing_timestamp": int(datetime(2021, month=7, day=1).timestamp()),
        "origin_project": "PLFSS 2022",
    },
    Path(
        f"{DATA_FOLDER}/exports_lectures/PLFSS 2021 JSON/lecture-an-15-3397-PO717460.json"
    ): {
        "default_processing_timestamp": int(datetime(2021, month=7, day=1).timestamp()),
        "origin_project": "PLFSS 2022",
    },
    Path(
        f"{DATA_FOLDER}/exports_lectures/PLFSS 2021 JSON/lecture-an-15-3397-PO420120.json"
    ): {
        "default_processing_timestamp": int(datetime(2021, month=7, day=1).timestamp()),
        "origin_project": "PLFSS 2022",
    },
    Path(
        f"{DATA_FOLDER}/exports_lectures/PLFSS 2022 - JSON/lecture-senat-2021-2022-118-PO78718.json"
    ): {
        "default_processing_timestamp": int(datetime(2022, month=7, day=1).timestamp()),
        "origin_project": "PLFSS 2023",
    },
    Path(
        f"{DATA_FOLDER}/exports_lectures/PLFSS 2022 - JSON/lecture-senat-2021-2022-189-PO78718.json"
    ): {
        "default_processing_timestamp": int(datetime(2022, month=7, day=1).timestamp()),
        "origin_project": "PLFSS 2023",
    },
    Path(
        f"{DATA_FOLDER}/exports_lectures/PLFSS 2022 - JSON/lecture-an-15-4685-PO717460.json"
    ): {
        "default_processing_timestamp": int(datetime(2022, month=7, day=1).timestamp()),
        "origin_project": "PLFSS 2023",
    },
    Path(
        f"{DATA_FOLDER}/exports_lectures/PLFSS 2022 - JSON/lecture-an-15-4523-PO717460.json"
    ): {
        "default_processing_timestamp": int(datetime(2022, month=7, day=1).timestamp()),
        "origin_project": "PLFSS 2023",
    },
    Path(
        f"{DATA_FOLDER}/exports_lectures/PLFSS 2023/lecture-senat-2022-2023-96-PO78718.json"
    ): {
        "default_processing_timestamp": int(datetime(2023, month=7, day=1).timestamp()),
        "origin_project": "PLFSS 2024",
    },
    Path(
        f"{DATA_FOLDER}/exports_lectures/PLFSS 2023/lecture-an-16-274-PO791932.json"
    ): {
        "default_processing_timestamp": int(datetime(2023, month=7, day=1).timestamp()),
        "origin_project": "PLFSS 2024",
    },
    Path(
        f"{DATA_FOLDER}/exports_lectures/PLFSS 2023/lecture-an-16-274-PO420120.json"
    ): {
        "default_processing_timestamp": int(datetime(2023, month=7, day=1).timestamp()),
        "origin_project": "PLFSS 2024",
    },
    Path(
        f"{DATA_FOLDER}/exports_lectures/PLFSS 2023/lecture-an-16-1682-PO791932 (2).json"
    ): {
        "default_processing_timestamp": int(datetime(2023, month=7, day=1).timestamp()),
        "origin_project": "PLFSS 2024",
    },
    Path(
        f"{DATA_FOLDER}/exports_lectures/PLFSS 2023/lecture-an-16-480-PO791932.json"
    ): {
        "default_processing_timestamp": int(datetime(2023, month=7, day=1).timestamp()),
        "origin_project": "PLFSS 2024",
    },
    Path(
        f"{DATA_FOLDER}/exports_lectures/Export PLFSS 2024/JSON/lecture-an-16-1682-PO420120.json"
    ): {
        "default_processing_timestamp": int(datetime(2024, month=7, day=1).timestamp()),
        "origin_project": "PLFSS 2025",
    },
    Path(
        f"{DATA_FOLDER}/exports_lectures/Export PLFSS 2024/JSON/lecture-an-16-1875-PO791932.json"
    ): {
        "default_processing_timestamp": int(datetime(2024, month=7, day=2).timestamp()),
        "origin_project": "PLFSS 2025",
    },
    Path(
        f"{DATA_FOLDER}/exports_lectures/Export PLFSS 2024/JSON/lecture-senat-2023-2024-77-PO78718.json"
    ): {
        "default_processing_timestamp": int(datetime(2024, month=7, day=3).timestamp()),
        "origin_project": "PLFSS 2025",
    },
}


PLACSS_FILE_CONFIG_JSON: dict[Path, InputFileConfig] = {
    Path(
        f"{DATA_FOLDER}/exports_lectures/PLACSS 22/AN Séance 1ère lecture/lecture-an-16-1268-PO791932.json"
    ): {
        "default_processing_timestamp": int(datetime(2022, month=7, day=1).timestamp()),
        "origin_project": "PLACSS 2021",
    },
    Path(
        f"{DATA_FOLDER}/exports_lectures/PLACSS 22/Sénat Séance 1ère lecture/lecture-senat-2022-2023-705-PO78718.json"
    ): {
        "default_processing_timestamp": int(datetime(2022, month=7, day=1).timestamp()),
        "origin_project": "PLACSS 2021",
    },
}

LFRSS_FILE_CONFIG_JSON: dict[Path, InputFileConfig] = {
    Path(
        f"{DATA_FOLDER}/exports_lectures/LFRSS 2023/lecture-an-16-760-PO791932.json"
    ): {
        "default_processing_timestamp": int(datetime(2023, month=7, day=1).timestamp()),
        "origin_project": "LFRSS 2023",
    },
    Path(
        f"{DATA_FOLDER}/exports_lectures/LFRSS 2023/lecture-an-16-760-PO420120.json"
    ): {
        "default_processing_timestamp": int(datetime(2023, month=7, day=1).timestamp()),
        "origin_project": "LFRSS 2023",
    },
    Path(
        f"{DATA_FOLDER}/exports_lectures/LFRSS 2023/lecture-senat-2022-2023-368-PO78718.json"
    ): {
        "default_processing_timestamp": int(datetime(2023, month=7, day=1).timestamp()),
        "origin_project": "LFRSS 2023",
    },
}

PPL_FILE_CONFIG_JSON: dict[Path, InputFileConfig] = {
    Path(
        f"{DATA_FOLDER}/exports_lectures/PPL LIOT 2023 abrogation réforme des retraites/Séance AN/lecture-an-16-1299-PO791932.json"
    ): {
        "default_processing_timestamp": int(datetime(2023, month=7, day=1).timestamp()),
        "origin_project": "PPL LIOT abrogation réforme des retraites",
    },
}

ALL_INPUT_FILE_CONFIGS_JSON = {
    **PLFSS_FILE_CONFIG_JSON,
    **PLACSS_FILE_CONFIG_JSON,
    **LFRSS_FILE_CONFIG_JSON,
    **PPL_FILE_CONFIG_JSON,
}

PLFSS_FILE_CONFIG_EXCEL: dict[Path, InputFileConfig] = {
    Path(
        f"{DATA_FOLDER}/exports_lectures/PLFSS 2025/BDD_AN_L1_SP_Amendements_copie_valeurs.xlsx"
    ): {
        "default_processing_timestamp": int(
            datetime(2024, month=10, day=17).timestamp()
        ),
        "origin_project": "PLFSS 2025",
    },
    Path(
        f"{DATA_FOLDER}/exports_lectures/PLFSS 2025/BDD_PLFSS_2025_SENAT_L1_SP.xlsx"
    ): {
        "default_processing_timestamp": int(
            datetime(2024, month=11, day=20).timestamp()
        ),
        "origin_project": "PLFSS 2025",
    },
}

PPL_FILE_CONFIG_EXCEL: dict[Path, InputFileConfig] = {
    Path(
        f"{DATA_FOLDER}/exports_lectures/PPL Retraites/2024/PPL_retraites_RN_BDD.xlsx"
    ): {
        "default_processing_timestamp": int(
            datetime(2024, month=10, day=1).timestamp()
        ),
        "origin_project": "PPL Retraites 2024",
    },
    Path(
        f"{DATA_FOLDER}/exports_lectures/PPL fin de vie 2024/BDD_Commission_PJL fin de vie.xlsx"
    ): {
        "default_processing_timestamp": int(
            datetime(2024, month=5, day=18).timestamp()
        ),
        "origin_project": "PPL Fin de vie 2024",
    },
}

PLF_FILE_CONFIG_EXCEL: dict[Path, InputFileConfig] = {
    Path(f"{DATA_FOLDER}/exports_lectures/PLF 2024/BDD_PLF_2024_SEN_L1_SP.xlsx"): {
        "default_processing_timestamp": int(
            datetime(2023, month=10, day=1).timestamp()
        ),
        "origin_project": "PLF 2024",
    },
    Path(
        f"{DATA_FOLDER}/exports_lectures/PLF 2025/BDD_PLF_2025_AN_L1_COM_Affaires_sociales.xlsx"
    ): {
        "default_processing_timestamp": int(
            datetime(2024, month=10, day=1).timestamp()
        ),
        "origin_project": "PLF 2025",
    },
    Path(
        f"{DATA_FOLDER}/exports_lectures/PLF 2025/BDD_PLF_2025_AN_L1_COM_Finances.xlsx"
    ): {
        "default_processing_timestamp": int(
            datetime(2024, month=11, day=1).timestamp()
        ),
        "origin_project": "PLF 2025",
    },
    Path(f"{DATA_FOLDER}/exports_lectures/PLF 2025/BDD_PLF_2025_AN_L1_SP.xlsx"): {
        "default_processing_timestamp": int(
            datetime(2024, month=12, day=1).timestamp()
        ),
        "origin_project": "PLF 2025",
    },
}

ALL_INPUT_FILE_CONFIGS_EXCEL = {
    **PLFSS_FILE_CONFIG_EXCEL,
    **PPL_FILE_CONFIG_EXCEL,
    **PLF_FILE_CONFIG_EXCEL,
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
    file_configs_json: dict[Path, Any],
    file_configs_excel: dict[Path, Any],
    acronym_mapping: dict[Acronym, str],
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
    for index, row in amendments_df.iterrows():
        amendments_df.at[index, "Corps amdt"] = (
            row["Corps amdt"]
            if pd.notna(row["Corps amdt"]) and row["Corps amdt"] not in [None, ""]
            else f"Ce corps d'amendement peut être ignoré, il a été ajouté pour faciliter le traitement des amendements {index}"
        )
    return amendments_df


def process_amendments(amendments_df: pd.DataFrame) -> pd.DataFrame:
    allotted_amdt_clusters = AllotmentHandler.get_clusters(
        amendments_df, group_by_columns=["Lecture", "origin_project", "Num article"]
    )
    return AllotmentHandler.filter_amdts_to_keep_one_per_allotment(
        normalized_amdt_df=amendments_df,
        allotted_amdt_clusters=allotted_amdt_clusters,
        removal_strategy_func=remove_oldest_and_without_response,
    )


def save_processed_amendments(df: pd.DataFrame, output_file: Path):
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
