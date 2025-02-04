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

import httpx
import pandas as pd
from unidecode import unidecode

from graal.allotment.allotment_handler import AllotmentHandler
from graal.attribution.attribution_data_loader import AttributionDataLoader
from graal.attribution.attribution_populator import AttributionPopulator
from graal.clustering.inadmissible_amdt_handler import InadmissibleAmendmentHandler
from graal.clustering.similarity_handler import SimilarityHandler
from graal.custom_types import ColumnsToWorkOn, InputFileConfig
from graal.opinion.opinion_handler import OpinionHandler
from graal.summary.llm_clients import (
    LLMAPIClient,
    OpenAIAPIClient,
)
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
    columns_to_clear = {"Commentaires"}
    columns_to_preserve = set()
    if args.allotments:
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
        columns_to_preserve.update(
            [
                "Sort",
                "Réponse",
            ]
        )
        columns_to_clear.update(["Sort", "Réponse"])

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
        f"{DATA_FOLDER}/preprocessed/pre_processed_old_amdts.pkl"
    )

    INPUT_FILES_CONFIG: dict[Path, InputFileConfig] = {
        Path(f"{DATA_FOLDER}/input_plfss/lecture-an-17-622-PO420120.json"): {
            "default_processing_timestamp": int(
                datetime(2025, month=1, day=23).timestamp()
            ),
            "origin_project": "PLFSS 2025",
            # "origin_project": "PPL Fin de vie",
        },
    }
    # INPUT_FILES_CONFIG: dict[FilePath, InputFileConfig] = {
    #     Path(f"{DATA_FOLDER}/input_ppl/lecture-an-17-475-PO838901.json"): {
    #         "default_processing_timestamp": int(
    #             datetime(2024, month=11, day=27).timestamp()
    #         ),
    #         "origin_project": "PPL Retraites",
    #     },
    # }
    # The results will be in OUTPUT_FILE_PREFIX.xlsx and OUTPUT_FILE_PREFIX.csv
    # OUTPUT_FILE_PREFIX = f"{DATA_FOLDER}/resultat_traitement_ppl_fin_vie_test_scaleway"
    OUTPUT_FILE_PREFIX = f"{DATA_FOLDER}/comparaison_semaine_dernière"
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
        "amdt_idx",
    ]

    columns_to_work_on = derive_columns_to_work_on_from_enabled_features(args)

    config_excel = pd.read_excel(GRAAL_CONFIG_FILE, sheet_name=None)

    llm_api_clients: list[LLMAPIClient] = []
    # for _ in range(7):
    #     ollama_api_client = OllamaAPIClient(
    #         endpoint=Url(os.environ["OLLAMA_ENDPOINT"]),
    #         model_name=os.environ["OLLAMA_MODEL_NAME"],
    #         user=os.environ["OLLAMA_USER"],
    #         password=os.environ["OLLAMA_PASSWORD"],
    #         timeout=30,
    #     )
    #     llm_api_clients.append(ollama_api_client)
    # for _ in range(6):
    #     llama_api_client = LLaMaAPIClient(
    #         model_name=os.environ["LLAMA_MODEL_NAME"],
    #         api_token=os.environ["LLAMA_API_KEY"],
    #     )
    #     llm_api_clients.append(llama_api_client)
    for _ in range(6):
        open_ai_api_client = OpenAIAPIClient(
            api_key=os.environ["SCALEWAY_API_KEY"],
            base_url=httpx.URL(os.environ["SCALEWAY_BASE_URL"]),
            model_name=os.getenv(
                "SCALEWAY_MODEL_NAME", "meta-llama/Meta-Llama-3.1-70B-Instruct"
            ),
        )
        llm_api_clients.append(open_ai_api_client)

    # for _ in range(6):
    #     albert_api_client = AlbertAPIClient(
    #         base_url=httpx.URL(
    #             os.getenv("ETALAB_BASE_URL", "https://albert.api.etalab.gouv.fr/v1")
    #         ),
    #         api_key=os.environ["ETALAB_API_KEY"],
    #         model_name=os.getenv(
    #             "ETALAB_MODEL_NAME", "meta-llama/Meta-Llama-3.1-70B-Instruct"
    #         ),
    #     )
    #     llm_api_clients.append(albert_api_client)

    # llm_api_clients.append(FakeLLMAPIClient())
    summary_gen_load_balancer = SummaryGenerationLoadBalancer(
        clients=llm_api_clients,
        queue_timeout=4,
        max_retries=5,
        rate_limiting_config={"albert": 100},
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
    # amendments_df = amendments_df[amendments_df["Num amdt"] == 614]
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

    if args.allotments:
        normalized_for_allot_df = AmendmentPreProcessor.drop_empty_rows_in_columns(
            amendments_df=intermediate_amdts_df,
            columns_to_filter=["Corps amdt"],
        )
        normalized_for_allot_df = AmendmentPreProcessor.handle_common_amendment_bodies(
            amendments_df=normalized_for_allot_df
        )
        normalized_for_allot_df = AmendmentPreProcessor.normalize_amendments(
            amendments_df=normalized_for_allot_df, columns_to_normalize=["Corps amdt"]
        )
        allotted_amdt_clusters = AllotmentHandler.get_clusters(
            normalized_amdt_df=normalized_for_allot_df, group_by_columns=["Num article"]
        )
        logging.info(
            f"Number of amendments before filterting out allotted amendements : {len(normalized_for_allot_df)}"
        )

        intermediate_amdts_df = AllotmentHandler.filter_amdts_to_keep_one_per_allotment(
            normalized_amdt_df=normalized_for_allot_df,
            allotted_amdt_clusters=allotted_amdt_clusters,
        )

        logging.info(
            f"Number of amendments left after removing extra allotted amendements : {len(intermediate_amdts_df)}"
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

    if args.attribution:
        amdt_with_attribution_df = intermediate_amdts_df
        amdt_with_attribution_df.loc[:, "Corps amdt"] = preprocessed_original_amdt_df[
            "Corps amdt"
        ].apply(lambda x: AttributionTextNormalizer.normalize_text(str(x)))

        amdt_with_attribution_df.loc[:, "Exposé amdt"] = amdt_with_attribution_df[
            "Exposé amdt"
        ].apply(lambda x: AttributionTextNormalizer.normalize_text(str(x)))

        attributor = AttributionPopulator(
            amendments_df=amdt_with_attribution_df,
            attribution_mappings_when_empty=AttributionDataLoader.load_default_attribution_mappings(
                config_excel
            ),
            codes_articles_df=AttributionDataLoader.load_codes_and_articles(
                config_excel
            ),
            laws_articles_df=AttributionDataLoader.load_laws_and_articles(config_excel),
            ordonnances_articles_df=AttributionDataLoader.load_ordonnances_and_articles(
                config_excel
            ),
            keywords_df=AttributionDataLoader.load_keywords(
                excel_data=config_excel, acronym_mapping=acronym_mapping
            ),
            name_to_user_info_mapping=AttributionDataLoader.load_name_to_user_info_mappings(
                config_excel
            ),
            interstitial_only=args.attribution_interstitial_only,
        )
        intermediate_amdts_df = attributor.populate()

    if args.similarity_search:
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
        )

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
