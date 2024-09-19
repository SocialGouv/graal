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
from amendements_intelligents.opinion.opinion_populator import OpinionPopulator
from amendements_intelligents.populate_allotments import AllotmentPopulator
from amendements_intelligents.populate_similarities import SimilarityPopulator
from amendements_intelligents.populate_summaries import SummaryPopulator
from amendements_intelligents.summary.llm_clients import FakeLLMAPIClient, LLMAPIClient
from amendements_intelligents.utils.amendment_pre_processor import AmendmentPreProcessor
from amendements_intelligents.utils.text_utils import AttributionTextNormalizer

logging.config.fileConfig("logging.conf")


def main():
    DATA_FOLDER = os.getenv("DATA_FOLDER")
    OUTPUT_FILE = f"{DATA_FOLDER}/full_pipeline_19_sept_15h"
    MAPPINGS_FILE = f"{DATA_FOLDER}/mappings_attributions_sept_19.xlsx"
    INPUT_FILE = (f"{DATA_FOLDER}/lecture-an-16-1682-PO791932.json", 2024)
    # INPUT_FILE = (f"{DATA_FOLDER}/lecture_PLACSS_2022.json", 2022)
    ACRONYM_FILE = f"{DATA_FOLDER}/acronym_mapping.xlsx"
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
    preprocessor = AmendmentPreProcessor
    amendments_df = preprocessor.load_amendments_json(input_files=[INPUT_FILE])
    acronym_mapping = preprocessor.load_acronyms_excel(acronym_file=ACRONYM_FILE)

    amendments_df = AmendmentPreProcessor.remap_columns_in_json_amendments(
        amendments_df
    )
    amendments_df = AmendmentPreProcessor.replace_acronyms(
        amendments_df=amendments_df,
        acronym_mapping=acronym_mapping,
        columns_to_normalize=["Exposé amdt", "Corps amdt"],
    )
    preprocessed_original_amdt_df = amendments_df.copy()
    # END LOAD AND PRE-PROCESS DATA

    # BEGIN SUMMARY GENERATION
    amendments_df = AmendmentPreProcessor.clear_columns_to_be_overridden(
        amendments_df=amendments_df, columns_to_clear=["Objet amdt"]
    )
    amdt_summary_populator = SummaryPopulator(
        llm_api_client=llm_api_client,
        amendments_df=amendments_df,
        acronym_mapping=acronym_mapping,
        summary_column="Objet amdt",
    )
    amdt_with_summaries_df = amdt_summary_populator.populate()
    # amdt_with_summaries_df.to_excel(f"{DATA_FOLDER}/amdt_with_summaries_df.xlsx")
    # END SUMMARY GENERATION

    # BEGIN ALLOTMENTS
    saved_amdt_df = amdt_with_summaries_df.copy()
    prepared_for_alot_df = AmendmentPreProcessor.clear_columns_to_be_overridden(
        amendments_df=amdt_with_summaries_df, columns_to_clear=["Allotissement"]
    )
    prepared_for_alot_df = AmendmentPreProcessor.remove_empty_rows_for_given_columns(
        amendments_df=prepared_for_alot_df, columns_to_filter_with=["Corps amdt"]
    )
    prepared_for_alot_df = AmendmentPreProcessor.handle_common_amendment_bodies(
        amendments_df=prepared_for_alot_df
    )
    prepared_for_alot_df = AmendmentPreProcessor.normalize_amendments(
        amendments_df=prepared_for_alot_df, columns_to_normalize=["Corps amdt"]
    )
    amdt_with_allotments_df = AllotmentPopulator.populate(
        original_amendments_df=saved_amdt_df,
        prepared_df=prepared_for_alot_df,
    )
    # amdt_with_allotments_df.to_excel(f"{DATA_FOLDER}/amdt_with_allotments_df.xlsx")
    # END ALLOTMENTS

    # BEGIN ATTRIBUTION
    amdt_with_attribution_df = amdt_with_allotments_df.copy()

    amdt_with_attribution_df = AmendmentPreProcessor.clear_columns_to_be_overridden(
        amendments_df=amdt_with_attribution_df,
        columns_to_clear=["Affectation (email)", "Affectation (nom)"],
    )
    # For this task, the normalization is slightly different than the one currently applied to
    # Corps amdt so I am taking the original text and normalizing it
    amdt_with_attribution_df["Corps amdt"] = preprocessed_original_amdt_df[
        "Corps amdt"
    ].apply(lambda x: AttributionTextNormalizer.normalize_text(str(x)))

    attribution_mappings_excel = pd.read_excel(MAPPINGS_FILE, sheet_name=None)
    codes_articles_df = AttributionDataLoader.load_codes_and_articles(
        attribution_mappings_excel
    )
    keywords_df = AttributionDataLoader.load_keywords(attribution_mappings_excel)
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
        input_files=[
            (f"{DATA_FOLDER}/PLFSS_2023.json", 2023),
            (f"{DATA_FOLDER}/PLFSS_2022.json", 2022),
            (f"{DATA_FOLDER}/PLFSS_2021.json", 2021),
        ]
    )
    old_amendments_df = SimilarityPopulator.preprocess_for_similarity(
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

    amdt_with_similarities_df = SimilarityPopulator.populate(
        preprocessed_old_amendments_df=old_amendments_df,
        preprocessed_new_amendments_df=new_amendments_df,
        original_new_amendments_df=saved_new_amendments_df,
    )
    result_df = amdt_with_similarities_df
    # END SIMILARITY SEARCH

    # BEGIN DEFAULT OPINION
    opinion_populator = OpinionPopulator(
        amendments_df=amdt_with_similarities_df,
        group_to_default_opinion=group_to_default_opinion,
    )

    amdt_with_opinions_df = opinion_populator.populate()
    result_df = amdt_with_opinions_df
    # END DEFAULT OPINION

    result_df.to_excel(f"{OUTPUT_FILE}.xlsx")
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
