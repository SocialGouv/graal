import logging
import logging.config
import os
import re

import pandas as pd

from amendements_intelligents.attribution.attribution_data_loader import (
    AttributionDataLoader,
)
from amendements_intelligents.attribution.plfss_attributor import PLFSSAttributor
from amendements_intelligents.populate_allotments import PLFSSAllotmentPopulator
from amendements_intelligents.populate_summaries import AmendmentSummaryPopulator
from amendements_intelligents.summary.llm_clients import (
    FakeLLMAPIClient,
    LLMAPIClient,
    LLMInferenceAPIClient,
)
from amendements_intelligents.utils.plfss_pre_processor import PLFSSPreProcessor
from amendements_intelligents.utils.plfss_text_utils import AttributionTextNormalizer

logging.config.fileConfig("logging.conf")


def main():
    DATA_FOLDER = os.getenv("DATA_FOLDER")
    OUTPUT_FILE = f"{DATA_FOLDER}/full_pipeline_df.xlsx"
    # MODEL_NAME = os.getenv("MODEL_NAME")
    # LLM_ENDPOINT = os.getenv("LLM_ENDPOINT")
    # USER = os.getenv("USER")
    # PASSWORD = os.getenv("PASSWORD")
    # llm_api_client: LLMAPIClient = LLMInferenceAPIClient(
    #     url=LLM_ENDPOINT,
    #     auth=(USER, PASSWORD),
    # )
    llm_api_client: LLMAPIClient = FakeLLMAPIClient()

    # BEGIN LOAD AND PRE-PROCESS DATA
    plfss_input_file = (f"{DATA_FOLDER}/PLFSS_2024.json", 2024)
    acronym_file = f"{DATA_FOLDER}/acronym_mapping.xlsx"
    mappings_file = f"{DATA_FOLDER}/mappings_attributions_aug_9.xlsx"
    SUMMARY_COLUMN = "Objet"

    preprocessor = PLFSSPreProcessor
    amendments_df = preprocessor.load_plfss_json(input_files=[plfss_input_file])
    acronym_mapping = preprocessor.load_acronyms_excel(acronym_file=acronym_file)

    amendments_df = PLFSSPreProcessor.remap_columns_in_json_amendments(amendments_df)
    cleaned_original_amdt_df = PLFSSPreProcessor.replace_acronyms(
        amendments_df=amendments_df,
        acronym_mapping=acronym_mapping,
        columns_to_normalize=["Exposé amdt", "Corps amdt"],
    )
    cleaned_original_amdt_df = PLFSSPreProcessor.prepare_amendments_columns(
        amendments_df=amendments_df
    )
    # END LOAD AND PRE-PROCESS DATA

    # BEGIN SUMMARY GENERATION
    amdt_summary_populator = AmendmentSummaryPopulator(
        llm_api_client=llm_api_client,
        amendments_df=cleaned_original_amdt_df,
        acronym_mapping=acronym_mapping,
        summary_column=SUMMARY_COLUMN,
    )
    cleaned_original_amdt_df[SUMMARY_COLUMN] = ""
    amdt_with_summaries_df = amdt_summary_populator.populate_summaries()
    # END SUMMARY GENERATION

    # BEGIN PRE-PROCESS FOR ALLOTMENTS
    prepared_for_alot_df = PLFSSPreProcessor.remove_empty_rows_for_given_columns(
        amendments_df=amdt_with_summaries_df, columns_to_filter_with=["Corps amdt"]
    )
    prepared_for_alot_df = PLFSSPreProcessor.handle_common_amendment_bodies(
        amendments_df=prepared_for_alot_df
    )
    prepared_for_alot_df = PLFSSPreProcessor.normalize_plfss(
        amendments_df=prepared_for_alot_df, columns_to_normalize=["Corps amdt"]
    )
    # END PRE-PROCESS FOR ALLOTMENTS

    # BEGIN ALLOTMENTS
    amdt_with_allotments_df = PLFSSAllotmentPopulator.populate(
        original_amendments_df=cleaned_original_amdt_df,
        prepared_df=prepared_for_alot_df,
    )
    # END ALLOTMENTS

    # BEGIN ATTRIBUTION
    amdt_with_attribution_df = amdt_with_allotments_df.copy()
    amdt_with_attribution_df["Corps amdt"] = amdt_with_allotments_df[
        "Corps amdt orig"
    ].apply(lambda x: AttributionTextNormalizer.normalize_text(str(x)))
    result_df = amdt_with_attribution_df

    attribution_mappings_excel = pd.read_excel(mappings_file, sheet_name=None)
    codes_articles_df = AttributionDataLoader.load_codes_and_articles(
        attribution_mappings_excel
    )
    keywords_df = AttributionDataLoader.load_keywords(attribution_mappings_excel)

    codes_set = set(codes_articles_df["Code"])
    max_code_length = codes_articles_df["Code"].str.len().max()
    articles_set = set(codes_articles_df["Articles"])
    pattern = re.compile(r"(?:\d+(?:-\d+)*)(?:\s(.+))?")
    latin_ordinals_set = {
        match.group(1)
        for article in articles_set
        if (match := pattern.match(article)) and match.group(1)
    }

    attributor = PLFSSAttributor(
        amendments_df=amdt_with_attribution_df,
        articles_set=articles_set,
        codes_articles_df=codes_articles_df,
        codes_set=codes_set,
        keywords_df=keywords_df,
        latin_ordinals_set=latin_ordinals_set,
        max_code_length=max_code_length,
    )
    amdt_with_attribution_df = attributor.populate()
    result_df = amdt_with_attribution_df
    # END ATTRIBUTION

    result_df.to_excel(OUTPUT_FILE)
    logging.info(
        f"Saved amendment with attribution, allotments and object to: {OUTPUT_FILE}"
    )


if __name__ == "__main__":
    main()
