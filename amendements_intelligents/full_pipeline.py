"""
This module serves as the main entry point for processing amendments related to
the French legislative process. It orchestrates the loading, preprocessing,
and analysis of amendment data, including generating summaries, allotments,
recurring amendements detection, attributions, and opinions.

Key functionalities include:
- Loading amendments and related data from JSON and Excel files.
- Preprocessing amendments to normalize and clean the data.
- Generating summaries for amendments using a language model.
- Populating allotments and attributions based on predefined mappings.
- Performing similarity searches between new and old amendments.
- Assigning default opinions based on group mappings.
- Saving the processed results to Excel and CSV formats.
"""

import logging
import logging.config
import os
import re
import time

import pandas as pd

from amendements_intelligents.attribution.attribution_data_loader import (
    AttributionDataLoader,
)
from amendements_intelligents.attribution.attribution_populator import (
    AttributionPopulator,
)
from amendements_intelligents.opinion.opinion_handler import OpinionHandler
from amendements_intelligents.populate_allotments import AllotmentHandler
from amendements_intelligents.populate_similarities import SimilarityHandler
from amendements_intelligents.populate_summaries import SummaryHandler
from amendements_intelligents.summary.llm_clients import (
    EtalabAPIClient,
    FakeLLMAPIClient,
    LLMAPIClient,
)
from amendements_intelligents.utils.amendment_pre_processor import AmendmentPreProcessor
from amendements_intelligents.utils.text_utils import AttributionTextNormalizer

logging.config.fileConfig("logging.conf")


def main():
    DATA_FOLDER = os.getenv("DATA_FOLDER")
    OUTPUT_FILE = f"{DATA_FOLDER}/PLFSS_2024"
    MAPPINGS_FILE = f"{DATA_FOLDER}/mappings_attributions_sept_21.xlsx"
    INPUT_FILE = (f"{DATA_FOLDER}/PLFSS_2024.json", 2022)
    ACRONYM_FILE = f"{DATA_FOLDER}/acronym_mapping.xlsx"
    COLUMNS_TO_OUTPUT_IN_EXCEL = [
        "Num amdt",
        "Allotissement",
        "Objet amdt",
        "Avis du Gouvernement",
        "Réponse",
        "Sort",
        "Affectation (email)",
        "Affectation (nom)",
        "Commentaires",
        "Exposé amdt",
        "Corps amdt",
    ]
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
        # (
        #     f"{DATA_FOLDER}/exports_lectures/Export PLFSS 2024/lecture-an-16-1682-PO791932.json",
        #     2024,
        # ),
        # (
        #     f"{DATA_FOLDER}/exports_lectures/Export PLFSS 2024/JSON/lecture-an-16-1682-PO420120.json",
        #     2024,
        # ),
        # (
        #     f"{DATA_FOLDER}/exports_lectures/Export PLFSS 2024/JSON/lecture-senat-2023-2024-77-PO78718 (1).json",
        #     2024,
        # ),
        # (
        #     f"{DATA_FOLDER}/exports_lectures/Export PLFSS 2024/JSON/lecture-an-16-1875-PO791932 (1).json",
        #     2024,
        # ),
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

    # MODEL_NAME = os.getenv("MODEL_NAME")
    # LLM_ENDPOINT = os.getenv("LLM_ENDPOINT")
    # USER = os.getenv("USER")
    # PASSWORD = os.getenv("PASSWORD")
    # llm_api_client: LLMAPIClient = LLMInferenceAPIClient(
    #     url=LLM_ENDPOINT,
    #     auth=(USER, PASSWORD),
    # )

    llm_api_client: LLMAPIClient = FakeLLMAPIClient()

    # llm_api_client: LLMAPIClient = EtalabAPIClient(
    #     base_url="https://albert.api.etalab.gouv.fr/v1",
    #     api_key=os.getenv("ETALAB_API_KEY"),
    #     model_name="meta-llama/Meta-Llama-3.1-70B-Instruct",
    # )

    # BEGIN LOAD AND PRE-PROCESS DATA
    amendments_df = AmendmentPreProcessor.load_amendments_json(input_files=[INPUT_FILE])
    acronym_mapping = AmendmentPreProcessor.load_acronyms_excel(
        acronym_file=ACRONYM_FILE
    )

    amendments_df = AmendmentPreProcessor.remap_columns_in_json_amendments(
        amendments_df
    )
    amendments_df = AmendmentPreProcessor.replace_acronyms(
        amendments_df=amendments_df,
        acronym_mapping=acronym_mapping,
        columns_to_normalize=["Exposé amdt", "Corps amdt"],
    )
    amendments_df["Commentaires"] = ""
    preprocessed_original_amdt_df = amendments_df.copy()
    # END LOAD AND PRE-PROCESS DATA

    # BEGIN ALLOTMENTS
    normalized_for_allot_df = AmendmentPreProcessor.clear_columns_to_be_overridden(
        amendments_df=amendments_df, columns_to_clear=["Allotissement"]
    )
    normalized_for_allot_df = AmendmentPreProcessor.remove_empty_rows_for_given_columns(
        amendments_df=normalized_for_allot_df, columns_to_filter_with=["Corps amdt"]
    )
    normalized_for_allot_df = AmendmentPreProcessor.handle_common_amendment_bodies(
        amendments_df=normalized_for_allot_df
    )
    normalized_for_allot_df = AmendmentPreProcessor.normalize_amendments(
        amendments_df=normalized_for_allot_df, columns_to_normalize=["Corps amdt"]
    )
    allotted_amdt_clusters = AllotmentHandler.get_clusters(
        normalized_amdt_df=normalized_for_allot_df
    )

    logging.info(
        f"Number of amendments before filterting out allotted amendements : {len(normalized_for_allot_df)}"
    )

    filtered_by_allot_df = AllotmentHandler.filter_amdts_to_keep_one_per_allotment(
        normalized_amdt_df=normalized_for_allot_df,
        allotted_amdt_clusters=allotted_amdt_clusters,
    )

    logging.info(
        f"Number of amendments left after removing extra allotted amendements : {len(filtered_by_allot_df)}"
    )

    # amdt_with_allotments_df.to_excel(f"{DATA_FOLDER}/amdt_with_allotments_df.xlsx")
    # END ALLOTMENTS

    # BEGIN SUMMARY GENERATION
    amdt_with_summaries_df = AmendmentPreProcessor.clear_columns_to_be_overridden(
        amendments_df=filtered_by_allot_df, columns_to_clear=["Objet amdt"]
    )
    amdt_summary_populator = SummaryHandler(
        llm_api_client=llm_api_client,
        amendments_df=amdt_with_summaries_df,
        acronym_mapping=acronym_mapping,
        summary_column="Objet amdt",
    )
    amdt_with_summaries_df = amdt_summary_populator.populate()
    # amdt_with_summaries_df.to_excel(f"{DATA_FOLDER}/amdt_with_summaries_df.xlsx")
    # END SUMMARY GENERATION

    # BEGIN ATTRIBUTION
    amdt_with_attribution_df = AmendmentPreProcessor.clear_columns_to_be_overridden(
        amendments_df=amdt_with_summaries_df,
        columns_to_clear=["Affectation (email)", "Affectation (nom)"],
    )
    # For this task, the normalization is slightly different than the one currently applied to
    # Corps amdt so I am taking the original text and normalizing it
    amdt_with_attribution_df.loc[:, "Corps amdt"] = preprocessed_original_amdt_df[
        "Corps amdt"
    ].apply(lambda x: AttributionTextNormalizer.normalize_text(str(x)))

    attribution_mappings_excel = pd.read_excel(MAPPINGS_FILE, sheet_name=None)
    codes_articles_df = AttributionDataLoader.load_codes_and_articles(
        attribution_mappings_excel
    )
    keywords_df = AttributionDataLoader.load_keywords(
        excel_data=attribution_mappings_excel, acronym_mapping=acronym_mapping
    )
    name_to_email_mapping = AttributionDataLoader.load_name_email_mappings(
        attribution_mappings_excel
    )
    attribution_mappings_when_empty = (
        AttributionDataLoader.load_default_attribution_mappings(
            attribution_mappings_excel
        )
    )
    group_to_default_opinion = AttributionDataLoader.load_group_to_default_opinion(
        attribution_mappings_excel
    )

    codes_set = set(codes_articles_df["Code"])
    max_code_length = codes_articles_df["Code"].str.len().max()
    articles_set = set(codes_articles_df["Articles"])
    pattern = re.compile(r"(?:\d+(?:-\d+)*)(?:\s(.+))?")
    latin_ordinals_set = {
        match.group(1)
        for article in articles_set
        if (match := pattern.match(article)) and match.group(1)
    }

    attributor = AttributionPopulator(
        amendments_df=amdt_with_attribution_df,
        articles_set=articles_set,
        attribution_mappings_when_empty=attribution_mappings_when_empty,
        codes_articles_df=codes_articles_df,
        codes_set=codes_set,
        keywords_df=keywords_df,
        latin_ordinals_set=latin_ordinals_set,
        max_code_length=max_code_length,
        name_to_email_mapping=name_to_email_mapping,
    )
    amdt_with_attribution_df = attributor.populate()
    # amdt_with_attribution_df.to_excel(f"{DATA_FOLDER}/amdt_with_attribution_df.xlsx")
    result_df = amdt_with_attribution_df

    # END ATTRIBUTION

    # BEGIN SIMILARITY SEARCH
    old_amendments_df = AmendmentPreProcessor.load_amendments_json(
        input_files=SIMILARITY_INPUT_FILES
    )
    old_amendments_df = SimilarityHandler.preprocess_for_similarity(
        amendments_df=old_amendments_df, acronym_mapping=acronym_mapping
    )

    new_amendments_df = amdt_with_attribution_df

    saved_new_amendments_df = new_amendments_df.copy()
    saved_new_amendments_df = AmendmentPreProcessor.clear_columns_to_be_overridden(
        amendments_df=saved_new_amendments_df, columns_to_clear=["Réponse", "Sort"]
    )

    new_amendments_df = AmendmentPreProcessor.normalize_amendments(
        amendments_df=new_amendments_df,
        columns_to_normalize=["Exposé amdt", "Objet amdt"],
    )

    new_amendments_df = AmendmentPreProcessor.remove_empty_rows_for_given_columns(
        amendments_df=new_amendments_df,
        columns_to_filter_with=["Exposé amdt", "Corps amdt"],
    )
    new_amendments_df = AmendmentPreProcessor.handle_common_amendment_bodies(
        amendments_df=new_amendments_df
    )
    new_amendments_df = AmendmentPreProcessor.handle_common_amendment_expose(
        amendments_df=new_amendments_df
    )

    amdt_with_similarities_df = SimilarityHandler.populate(
        preprocessed_old_amendments_df=old_amendments_df,
        preprocessed_new_amendments_df=new_amendments_df,
        original_new_amendments_df=saved_new_amendments_df,
    )
    result_df = amdt_with_similarities_df
    # END SIMILARITY SEARCH

    # BEGIN DEFAULT OPINION
    opinion_populator = OpinionHandler(
        amendments_df=amdt_with_similarities_df,
        group_to_default_opinion=group_to_default_opinion,
    )

    amdt_with_opinions_df = opinion_populator.populate()
    result_df = amdt_with_opinions_df
    # END DEFAULT OPINION

    # BEGIN ALIGNING ALL ALLOTED AMENDMENTS
    amdt_with_allotments_df = AllotmentHandler.populate(
        original_amendments_df=preprocessed_original_amdt_df,
        pipeline_result_amdt_df=amdt_with_opinions_df,
        allotted_amdt_clusters=allotted_amdt_clusters,
        columns_to_copy=[
            "Réponse",
            "Sort",
            "Commentaires",
            "Objet amdt",
            "Avis du Gouvernement",
            "Affectation (email)",
            "Affectation (nom)",
        ],
    )
    result_df = amdt_with_allotments_df
    # END ALIGNING ALL ALLOTED AMENDMENTS

    result_df[COLUMNS_TO_OUTPUT_IN_EXCEL].to_excel(f"{OUTPUT_FILE}.xlsx")
    logging.info(
        f"Saved amendment with attribution, allotments and object to: {OUTPUT_FILE}.xlsx"
    )
    result_df.to_csv(
        f"{OUTPUT_FILE}.csv",
        sep=";",
        encoding="utf-8-sig",
        index=False,
    )

    logging.info(
        f"Saved amendment with attribution, allotments and object to: {OUTPUT_FILE}.csv"
    )


if __name__ == "__main__":
    start_time = time.time()
    main()
    end_time = time.time()
    logging.info(f"Total execution time: {end_time - start_time} seconds")
