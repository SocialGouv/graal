import os

from amendements_intelligents.populate_allotments import PLFSSAllotmentPopulator
from amendements_intelligents.populate_summaries import AmendmentSummaryPopulator
from amendements_intelligents.summary.llm_clients import FakeLLMAPIClient, LLMAPIClient
from amendements_intelligents.utils.plfss_pre_processor import PLFSSPreProcessor

MODEL_NAME = os.getenv("MODEL_NAME")
DATA_FOLDER = os.getenv("DATA_FOLDER")
VLLM_ENDPOINT = os.getenv("VLLM_ENDPOINT")
USER = os.getenv("USER")
PASSWORD = os.getenv("PASSWORD")


def main():
    # llm_api_client: LLMAPIClient = LLMInferenceAPIClient(
    #     url="http://localhost:8000/generate"
    # )

    # BEGIN LOAD AND PRE-PROCESS DATA
    plfss_input_file = (f"{DATA_FOLDER}/PLFSS_2024.json", 2024)
    acronym_file = f"{DATA_FOLDER}/acronym_mapping.xlsx"
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
    llm_api_client: LLMAPIClient = FakeLLMAPIClient()
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

    amdt_with_allotments_df.to_excel("data/amdt_with_allotments_and_object_df.xlsx")


if __name__ == "__main__":
    main()
