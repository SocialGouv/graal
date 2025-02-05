"""
This module preprocesses old amendments for similarity search.

It includes functions to load and preprocess amendments from JSON and Excel files,
process the amendments to filter and cluster them (in order to remove duplicates), and save the processed amendments
to a file. These will then be used to populate similarities between old and new amendments in the amendement processing pipeline.
"""

import argparse
import logging
import logging.config
import os
import pickle  # nosec
import time
from pathlib import Path
from typing import Any

import pandas as pd
from unidecode import unidecode

from graal.allotment.allotment_handler import AllotmentHandler
from graal.clustering.similarity_handler import SimilarityHandler
from graal.custom_types import Acronym, IntIndex
from graal.utils.amendment_pre_processor import AmendmentPreProcessor
from graal.utils.config.project_config_manager import ProjectConfigManager
from graal.utils.text_utils import remove_gage_sentences

logging.config.fileConfig("logging.conf")

DATA_FOLDER = os.getenv("DATA_FOLDER", "data")
DEFAULT_OUTPUT_FILE = Path(f"{DATA_FOLDER}/preprocessed/pre_processed_old_amdts.pkl")
ATTRIBUTION_MAPPINGS_FILE = Path(
    f"{DATA_FOLDER}/config_graal/Fichier de configuration GRAAL - DSS - latest.xlsx"
)


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Preprocess old amendments for similarity search."
    )
    parser.add_argument(
        "--projects",
        nargs="*",
        choices=list(ProjectConfigManager.AVAILABLE_PROJECTS.keys()),
        help="List of projects to include (e.g., PLFSS PLACSS). If not specified, includes all projects.",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output pickle file path (default: data/preprocessed/pre_processed_old_amdts.pkl)",
        default=DEFAULT_OUTPUT_FILE,
    )
    args = parser.parse_args()
    return args.projects, Path(args.output)


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
    if file_configs_json:
        amendments_df_json = AmendmentPreProcessor.load_amendments_json(
            list(file_configs_json.keys()), file_configs_json
        )
        amendments_df_json = SimilarityHandler.preprocess_for_similarity(
            amendments_df_json, acronym_mapping
        )
    else:
        amendments_df_json = pd.DataFrame()
    if file_configs_excel:
        amendments_df_excel = AmendmentPreProcessor.load_amendments_excel(
            list(file_configs_excel.keys()), file_configs_excel
        )
        amendments_df_excel = SimilarityHandler.preprocess_for_similarity(
            amendments_df_excel, acronym_mapping
        )
    else:
        amendments_df_excel = pd.DataFrame()

    if not amendments_df_json.empty and not amendments_df_excel.empty:
        amendments_df = AmendmentPreProcessor.concatenate_dataframes(
            amendments_df_json, amendments_df_excel
        )
    elif not amendments_df_json.empty:
        amendments_df = amendments_df_json
    else:
        amendments_df = amendments_df_excel

    amendments_df = AmendmentPreProcessor.drop_empty_rows_in_columns(
        amendments_df, ["Réponse"]
    )
    amendments_df["Corps amdt"] = amendments_df["Corps amdt"].apply(
        lambda text: remove_gage_sentences(unidecode(text))
    )
    amendments_df["Exposé amdt"] = amendments_df["Exposé amdt"].apply(
        lambda text: remove_gage_sentences(unidecode(text))
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
    # Parse command line arguments
    project_names, output_file = parse_args()

    # Load project configurations
    project_config = ProjectConfigManager.get_project_configs(project_names)
    if project_names:
        logging.info(f"Processing amendments for projects: {', '.join(project_names)}")
    else:
        logging.info("Processing amendments for all projects")

    # Load and process amendments
    attribution_mappings_excel = pd.read_excel(
        ATTRIBUTION_MAPPINGS_FILE, sheet_name=None
    )
    acronym_mapping = AmendmentPreProcessor.load_acronyms(
        attribution_mappings_excel["Acronymes"]
    )
    amendments_df = load_and_preprocess_amendments(
        project_config.json_configs,
        project_config.excel_configs,
        acronym_mapping=acronym_mapping,
    )
    processed_df = process_amendments(amendments_df)
    logging.info(
        f"Number of old amendments available for similarity search: {len(processed_df)}"
    )
    save_processed_amendments(processed_df, output_file)


if __name__ == "__main__":
    start_time = time.time()
    main()
    end_time = time.time()
    logging.info(f"Total execution time: {end_time - start_time:.2f} seconds")
