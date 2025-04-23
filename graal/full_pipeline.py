"""
This module serves as the main entry point for processing amendments related to
the French legislative process. It orchestrates the loading, preprocessing,
and analysis of amendment data, including generating summaries, allotments,
recurring amendments detection, attributions, and opinions.

Key functionalities include:
- Loading amendments and related data from JSON and Excel files.
- Preprocessing amendments to normalize and clean the data.
- Generating summaries for amendments using a language model.
- Populating allotments and attributions based on predefined mappings.
- Performing similarity searches between new and old amendments.
- Assigning default opinions based on group mappings.
- Handling previously identified inadmissible amendments by processing them separately.
- Adding placeholder text for empty amendment bodies.
- Ignoring already processed amendments based on a provided list.
- Saving the processed results to Excel and CSV formats.
"""

import argparse
import json
import logging
import logging.config
import os
import re
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
from unidecode import unidecode

from graal.allotment.allotment_handler import AllotmentHandler
from graal.attribution.attribution_data_loader import AttributionDataLoader
from graal.attribution.project_configurations import (
    get_attribution_handler_builder_func,
)
from graal.clustering.inadmissible_amdt_handler import InadmissibleAmendmentHandler
from graal.clustering.similarity_handler import SimilarityHandler
from graal.custom_types import ColumnsToWorkOn, InputFileConfig, IntIndex
from graal.opinion.opinion_handler import OpinionHandler
from graal.similarities.similarities_handler import SimilaritiesHandler
from graal.summary.llm_factory import create_llm_api_clients, get_rate_limiting_config
from graal.summary.summary_generation_load_balancer import SummaryGenerationLoadBalancer
from graal.summary.summary_handler import SummaryHandler
from graal.utils.amendment_pre_processor import AmendmentPreProcessor
from graal.utils.text_utils import (
    AttributionTextNormalizer,
    remove_gage_sentences,
)

logging.config.fileConfig("logging.conf")


def load_config(config_path: str) -> argparse.Namespace:
    with open(config_path, "r", encoding="UTF-8") as file:
        config = json.load(file)
    return argparse.Namespace(**config)


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Process amendments related to the French legislative process."
    )
    parser.add_argument(
        "--config", type=str, required=True, help="Path to the JSON configuration file."
    )
    args = parser.parse_args()
    return load_config(args.config)


def derive_columns_to_work_on_from_enabled_features(
    args: argparse.Namespace,
) -> ColumnsToWorkOn:
    """
    Derive columns to work on based on enabled features in the configuration.

    Returns:
        ColumnsToWorkOn: An object containing sets of column names to preserve or clear
        based on enabled features in the configuration.
    """
    columns_to_clear = {"Commentaires"}
    columns_to_preserve = set()
    if args.allotments.get("enabled", False):
        columns_to_clear.update(["Allotissement"])

    if args.summary_generation:
        columns_to_preserve.update(["Objet amdt"])
        columns_to_clear.update(["Objet amdt"])

    if args.attribution:
        columns_to_preserve.update(
            [
                "Affectation (email)",
                "Affectation (nom)",
                "Entité Pilote",
            ]
        )
        columns_to_clear.update(
            ["Affectation (email)", "Affectation (nom)", "Entité Pilote"]
        )

    if args.similarity_search:
        # Extract similarity search configuration
        similarity_config = (
            args.similarity_search
            if isinstance(args.similarity_search, dict)
            else {"enabled": False}
        )

        # Only add columns if similarity search is enabled
        if similarity_config.get("enabled", False):
            columns_to_copy_config = similarity_config.get("columns_to_copy", {})

            # Add columns that are enabled for copying to preserve and clear lists
            columns_to_preserve_list = []
            columns_to_clear_list = []

            for column, config in columns_to_copy_config.items():
                if config.get("enabled", False):
                    columns_to_preserve_list.append(column)
                    columns_to_clear_list.append(column)

            columns_to_preserve.update(columns_to_preserve_list)
            columns_to_clear.update(columns_to_clear_list)

    if args.default_opinion:
        columns_to_preserve.update(["Avis du Gouvernement"])
        columns_to_clear.update(["Avis du Gouvernement"])

    columns_to_work_on = ColumnsToWorkOn(
        to_preserve_orig_value=columns_to_preserve, to_clear=columns_to_clear
    )
    return columns_to_work_on


# ruff: noqa: C901
def run_processing_pipeline(args: argparse.Namespace) -> None:
    DATA_FOLDER = os.getenv("DATA_FOLDER")
    GRAAL_CONFIG_FILE = Path(
        f"{DATA_FOLDER}/config_graal/Fichier de configuration GRAAL - DSS - latest.xlsx"
    )
    PREPROCESSED_INADMISSIBLE_FILE = Path(
        f"{DATA_FOLDER}/preprocessed/inadmissible_commission.pkl"
    )
    PRE_PROCESSED_OLD_AMENDMENTS_FILE = Path(
        # f"{DATA_FOLDER}/preprocessed/plfss_similarity_db.pkl"
        f"{DATA_FOLDER}/preprocessed/ppl_similarity_db.pkl"
    )

    INPUT_FILES_CONFIG: dict[Path, InputFileConfig] = {
        # Path(f"{DATA_FOLDER}/input_plfss/lecture-an-17-622-PO838901.json"): {
        Path(f"{DATA_FOLDER}/input_ppl_fin_vie/AN_Séance publique_PPL_SPA.json"): {
            "default_processing_timestamp": int(
                datetime(year=2025, month=4, day=5).timestamp()
            ),
            "origin_project": "PPL Fin de vie 2025",
        }
    }
    # The results will be in OUTPUT_FILE_PREFIX.xlsx and OUTPUT_FILE_PREFIX.csv
    OUTPUT_FILE_PREFIX = f"{DATA_FOLDER}/résultats_ppl_SPA_2025"
    COLUMNS_TO_OUTPUT_IN_EXCEL = [
        "Num amdt",
        "Commentaires",
        "Allotissement",
        "Objet amdt",
        "Sort",
        "Réponse",
        "Affectation (email)",
        "Affectation (nom)",
        "Entité Pilote",
        "Avis du Gouvernement",
        "Groupe",
        "Num article",
        "Exposé amdt",
        "Corps amdt",
        # "mission_titre_court",
        "amdt_idx",
    ]

    columns_to_work_on = derive_columns_to_work_on_from_enabled_features(args)

    config_excel = pd.read_excel(GRAAL_CONFIG_FILE, sheet_name=None)

    # Create LLM API clients based on configuration
    llm_api_clients = create_llm_api_clients(vars(args))

    # Get rate limiting configuration
    rate_limiting_config = get_rate_limiting_config(vars(args))

    summary_gen_load_balancer = SummaryGenerationLoadBalancer(
        clients=llm_api_clients,
        queue_timeout=4,
        max_retries=5,
        rate_limiting_config=rate_limiting_config,
    )

    intermediate_amdts_df = None

    # amendments_df = AmendmentPreProcessor.load_amendments_excel(
    #     list(INPUT_FILES_CONFIG.keys()), INPUT_FILES_CONFIG
    # )

    amendments_df = AmendmentPreProcessor.load_amendments_json(
        list(INPUT_FILES_CONFIG.keys()), INPUT_FILES_CONFIG
    )

    if args.mission_short_title_filter and len(args.mission_short_title_filter) > 0:
        amendments_df["mission_titre_court"] = (
            amendments_df["mission_titre_court"]
            .str.normalize("NFKD")
            .str.encode("ascii", errors="ignore")
            .str.decode("utf-8")
            .str.lower()
        )
        amendments_df = amendments_df[
            amendments_df["mission_titre_court"].apply(
                lambda x: any(
                    x.startswith(prefix) for prefix in args.mission_short_title_filter
                )
            )
        ]

    amendments_df = AmendmentPreProcessor.remap_columns_in_json_amendments(
        amendments_df
    )
    # amendments_df = amendments_df[amendments_df["Num amdt"].isin([196, 923, 1111])]
    original_amdt_df = amendments_df.copy()

    if args.placeholder_amdt_body:
        for index, row in amendments_df.iterrows():
            amendments_df.at[index, "Corps amdt"] = (
                row["Corps amdt"]
                if pd.notna(row["Corps amdt"]) and row["Corps amdt"] not in [None, ""]
                else f"Ce corps d'amendement peut être ignoré, il a été ajouté pour faciliter le traitement des amendements {index}"
            )

    if len(args.already_processed_amdt_nums_path) > 0:
        with open(args.already_processed_amdt_nums_path, "r", encoding="UTF-8") as file:
            amdt_nums = {int(line.strip()) for line in file}
        amendments_df = amendments_df[~amendments_df["Num amdt"].isin(amdt_nums)]
        print(f"Ignoring num amdts: {amdt_nums}")

    acronym_mapping = AmendmentPreProcessor.load_acronyms(config_excel["Acronymes"])
    amendments_df = AmendmentPreProcessor.drop_empty_rows_in_columns(
        amendments_df=amendments_df,
        columns_to_filter=["Exposé amdt"],
    )
    amendments_df = AmendmentPreProcessor.replace_acronyms(
        amendments_df=amendments_df,
        acronym_mapping=acronym_mapping,
        columns_to_normalize=["Exposé amdt", "Corps amdt"],
    )

    amendments_df["Corps amdt"] = amendments_df["Corps amdt"].apply(
        lambda text: remove_gage_sentences(unidecode(text))
    )

    amendments_df["Exposé amdt"] = amendments_df["Exposé amdt"].apply(
        lambda text: remove_gage_sentences(unidecode(text))
    )

    amendments_df = AmendmentPreProcessor.clear_columns_to_be_overridden(
        amendments_df=amendments_df,
        columns_to_clear=columns_to_work_on["to_clear"],
    )
    intermediate_amdts_df = amendments_df
    preprocessed_original_amdt_df = amendments_df.copy()

    amdt_allotment_strategy_func = AllotmentHandler.default_removal_strategy_func

    if args.attribution:
        amdt_with_attribution_df = intermediate_amdts_df
        amdt_with_attribution_df.loc[:, "Corps amdt"] = preprocessed_original_amdt_df[
            "Corps amdt"
        ].apply(lambda x: AttributionTextNormalizer.normalize_text(str(x)))

        amdt_with_attribution_df.loc[:, "Exposé amdt"] = amdt_with_attribution_df[
            "Exposé amdt"
        ].apply(lambda x: AttributionTextNormalizer.normalize_text(str(x)))

        builder_func = get_attribution_handler_builder_func(
            args.attribution_project_name
        )
        attribution_handler = builder_func(config_excel)

        if args.attribution_interstitial_only:
            relevant_amendments_df = amendments_df[
                amendments_df["Num article"].str.lower().str.startswith("article add.")
            ].copy()
        else:
            relevant_amendments_df = amendments_df.copy()

        intermediate_amdts_df = attribution_handler.process_amendments(
            relevant_amendments_df
        )

        default_attributions = AttributionDataLoader.load_default_attribution_mappings(
            config_excel
        )

        def build_attribution_allot_filter_func(default_attributions):
            def removal_func(amendments_df: pd.DataFrame, cluster: list[IntIndex]):
                affectation_series = amendments_df.loc[
                    amendments_df["amdt_idx"].isin(cluster)
                    & ~amendments_df["Affectation (nom)"].isin(default_attributions),
                    "Affectation (nom)",
                ]
                if affectation_series.empty:
                    return cluster[1:]
                most_common_affectation = affectation_series.value_counts().idxmax()
                affectation_df = amendments_df.loc[
                    (amendments_df["Affectation (nom)"] == most_common_affectation)
                    & (amendments_df["amdt_idx"].isin(cluster)),
                    "amdt_idx",
                ]
                if not affectation_df.empty:
                    amdt_idx_with_most_common_affectation = affectation_df.iloc[0]
                else:
                    amdt_idx_with_most_common_affectation = None

                to_remove = [
                    idx
                    for idx in cluster
                    if idx != amdt_idx_with_most_common_affectation
                ]
                return to_remove

            return removal_func

        amdt_allotment_strategy_func = build_attribution_allot_filter_func(
            default_attributions
        )

    # Extract allotment configuration
    allotment_config = args.allotments
    allotment_enabled = allotment_config.get("enabled", False)
    tf_idf_threshold = getattr(args, "tf_idf_threshold", 0.0001)

    if allotment_enabled:
        allotment_column = allotment_config.get("column", None)
        if allotment_column is None:
            raise ValueError(
                "Allotment column must be specified in the configuration under 'column'."
            )
        similarity_threshold = allotment_config.get("similarity_threshold", 0.0001)
        normalized_for_allot_df = AmendmentPreProcessor.drop_empty_rows_in_columns(
            amendments_df=intermediate_amdts_df,
            columns_to_filter=[allotment_column],
        )
        normalized_for_allot_df = AmendmentPreProcessor.handle_common_amendment_bodies(
            amendments_df=normalized_for_allot_df
        )
        normalized_for_allot_df = AmendmentPreProcessor.normalize_amendments(
            amendments_df=normalized_for_allot_df,
            columns_to_normalize=[allotment_column],
        )
        cluster_finder, tfidf_clusters = AllotmentHandler.create_tfidf_clusters(
            normalized_amdt_df=normalized_for_allot_df,
            group_by_columns=["Num article"],
            eps=tf_idf_threshold,
        )
        allotted_amdt_clusters = AllotmentHandler.apply_levenshtein_refinement(
            cluster_finder=cluster_finder,
            threshold=similarity_threshold,
        )
        logging.info(
            f"Number of amendments before filterting out allotted amendements : {len(normalized_for_allot_df)}"
        )

        intermediate_amdts_df = AllotmentHandler.filter_amdts_to_keep_one_per_allotment(
            normalized_amdt_df=normalized_for_allot_df,
            allotted_amdt_clusters=allotted_amdt_clusters,
            removal_strategy_func=amdt_allotment_strategy_func,
        )

        logging.info(
            f"Number of amendments left after removing extra allotted amendements : {len(intermediate_amdts_df)}"
        )

    # Extract similarities_within_lectures configuration
    similarities_config = args.similarities_within_lectures
    similarities_enabled = similarities_config.get("enabled", False)

    if similarities_enabled:
        similarities_column = similarities_config.get("column", None)
        if similarities_column is None:
            raise ValueError(
                "Similarities column must be specified in the configuration under 'column'."
            )
        similarity_threshold = similarities_config.get("similarity_threshold", 0.8)

        normalized_for_similarities_df = (
            AmendmentPreProcessor.drop_empty_rows_in_columns(
                amendments_df=intermediate_amdts_df,
                columns_to_filter=[similarities_column],
            )
        )
        normalized_for_similarities_df = (
            AmendmentPreProcessor.handle_common_amendment_bodies(
                amendments_df=normalized_for_similarities_df
            )
        )
        normalized_for_similarities_df = AmendmentPreProcessor.normalize_amendments(
            amendments_df=normalized_for_similarities_df,
            columns_to_normalize=[similarities_column],
        )

        cluster_finder, tfidf_clusters = SimilaritiesHandler.create_tfidf_clusters(
            normalized_amdt_df=normalized_for_similarities_df,
            group_by_columns=["Num article"],
            eps=tf_idf_threshold,
        )

        similar_amdt_clusters = SimilaritiesHandler.apply_levenshtein_refinement(
            cluster_finder=cluster_finder,
            threshold=similarity_threshold,
        )

        similarity_percentages = SimilaritiesHandler.calculate_similarity_percentages(
            normalized_amdt_df=normalized_for_similarities_df,
            allotted_amdt_clusters=similar_amdt_clusters,
        )

        intermediate_amdts_df = SimilaritiesHandler.update_comments_with_similarities(
            amendments_df=intermediate_amdts_df,
            similarity_percentages=similarity_percentages,
            threshold=similarity_threshold,
        )

        logging.info(
            f"Updated comments with similarity information for {len(similarity_percentages)} amendments"
        )

    if args.similarity_search:
        # Extract similarity search configuration
        similarity_config = (
            args.similarity_search
            if isinstance(args.similarity_search, dict)
            else {"enabled": False}
        )

        # Get columns to copy configuration with defaults (all disabled)
        columns_to_copy_config = similarity_config.get(
            "columns_to_copy",
            {
                "Réponse": {"enabled": False},
                "Sort": {"enabled": False, "condition": "irrecevable"},
                "Objet": {"enabled": False},
            },
        )

        old_amendments_df = pd.read_pickle(PRE_PROCESSED_OLD_AMENDMENTS_FILE)  # nosec
        logging.info(f"Loaded old amendments from: {PRE_PROCESSED_OLD_AMENDMENTS_FILE}")
        new_amendments_df = intermediate_amdts_df
        saved_new_amendments_df = new_amendments_df.copy()
        new_amendments_df = AmendmentPreProcessor.drop_empty_rows_in_columns(
            amendments_df=new_amendments_df,
            columns_to_filter=["Exposé amdt", "Corps amdt"],
        )
        new_amendments_df = AmendmentPreProcessor.normalize_amendments(
            new_amendments_df, columns_to_normalize=["Exposé amdt", "Corps amdt"]
        )
        new_amendments_df = AmendmentPreProcessor.handle_common_amendment_bodies(
            amendments_df=new_amendments_df
        )
        new_amendments_df = AmendmentPreProcessor.handle_common_amendment_expose(
            amendments_df=new_amendments_df
        )
        intermediate_amdts_df = SimilarityHandler.populate(
            preprocessed_old_amendments_df=old_amendments_df,
            preprocessed_new_amendments_df=new_amendments_df,
            original_new_amendments_df=saved_new_amendments_df,
            clustering_similarity_thresholds={
                "Exposé amdt": 0.4,
                "Corps amdt": 0.4,
            },
            fuzzy_match_similarity_thresholds={
                "Exposé amdt": 0.4,
                "Corps amdt": 0.9,
            },
            similarity_threshold_overrides={
                "Exposé amdt": {"amendement redactionnel": 0.95},
            },
            column_filtering_funcs={
                "Corps amdt": SimilarityHandler.filter_old_amendments_by_project,
            },
            column_group_by_columns={
                "Corps amdt": ["Num article"],
            },
            columns_to_copy_config=columns_to_copy_config,
        )

    if args.summary_generation:
        config_prompt = config_excel["Prompt Objet"].to_string()
        amdt_summary_populator = SummaryHandler(
            summary_gen_load_balancer=summary_gen_load_balancer,
            amendments_df=intermediate_amdts_df,
            acronym_mapping=acronym_mapping,
            summary_column="Objet amdt",
            config_prompt=config_prompt,
        )
        intermediate_amdts_df = amdt_summary_populator.populate()

    if args.allotments:
        intermediate_amdts_df = AllotmentHandler.populate(
            original_amendments_df=preprocessed_original_amdt_df,
            pipeline_result_amdt_df=intermediate_amdts_df,
            allotted_amdt_clusters=allotted_amdt_clusters,  # type: ignore
            columns_to_copy=[
                "Réponse",
                "Sort",
                "Commentaires",
                "Objet amdt",
                "Avis du Gouvernement",
                "Affectation (email)",
                "Affectation (nom)",
                "Entité Pilote",
            ],
        )

    if args.default_opinion:
        opinion_populator = OpinionHandler(
            amendments_df=intermediate_amdts_df,
            group_to_default_opinion=AttributionDataLoader.load_group_to_default_opinion(
                config_excel
            ),
        )
        intermediate_amdts_df = opinion_populator.populate()
        if args.allotments:
            for allot, group in intermediate_amdts_df.groupby("Allotissement"):
                if "Défavorable" in group["Avis du Gouvernement"].values:
                    intermediate_amdts_df.loc[
                        intermediate_amdts_df["Allotissement"] == allot,
                        "Avis du Gouvernement",
                    ] = "Défavorable"

    if args.summary_generation:
        regex_pattern = r"amendements? d.?appel"
        mask = intermediate_amdts_df["Exposé amdt"].apply(
            lambda x: isinstance(x, str)
            and re.search(regex_pattern, x, re.IGNORECASE) is not None
        ) & (intermediate_amdts_df["Objet amdt"] != "Supprimer cet article.")
        intermediate_amdts_df.loc[mask, "Objet amdt"] = (
            "APPEL : " + intermediate_amdts_df.loc[mask, "Objet amdt"]
        )

    if args.handle_inadmissible_amendments:
        inadmissible_amdt_handler = InadmissibleAmendmentHandler(
            preprocessed_inadmissible_file=PREPROCESSED_INADMISSIBLE_FILE
        )
        intermediate_amdts_df = inadmissible_amdt_handler.process(
            amendments_df=intermediate_amdts_df
        )

    if args.no_value_overwrite:
        for column in columns_to_work_on["to_preserve_orig_value"]:
            intermediate_amdts_df[column] = intermediate_amdts_df.apply(
                lambda row, col=column: (
                    original_value := original_amdt_df.loc[
                        original_amdt_df["amdt_idx"] == row["amdt_idx"], col
                    ].values[0],
                    original_value
                    if pd.notna(original_value) and original_value not in [None, ""]
                    else row[col],
                )[1],
                axis=1,
            )

    intermediate_amdts_df.to_excel(
        f"{OUTPUT_FILE_PREFIX}.xlsx", columns=COLUMNS_TO_OUTPUT_IN_EXCEL
    )
    intermediate_amdts_df.to_csv(
        f"{OUTPUT_FILE_PREFIX}.csv", sep=";", encoding="utf-8-sig", index=False
    )
    logging.info(
        f"Saved processed amendments to: {OUTPUT_FILE_PREFIX}.xlsx and {OUTPUT_FILE_PREFIX}.csv"
    )


if __name__ == "__main__":
    start_time = time.time()
    args = parse_arguments()
    run_processing_pipeline(args)
    end_time = time.time()
    logging.info(f"Total execution time: {end_time - start_time} seconds")
