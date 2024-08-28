import os

from amendements_intelligents.populate_summaries import AmendmentSummaryPopulator
from amendements_intelligents.summary.llm_clients import (
    LLMAPIClient,
    LLMInferenceAPIClient,
)
from amendements_intelligents.utils.plfss_pre_processor import PLFSSPreProcessor

MODEL_NAME = os.getenv("MODEL_NAME")
DATA_FOLDER = os.getenv("DATA_FOLDER")
VLLM_ENDPOINT = os.getenv("VLLM_ENDPOINT")
USER = os.getenv("USER")
PASSWORD = os.getenv("PASSWORD")


def main():
    llm_api_client: LLMAPIClient = LLMInferenceAPIClient(
        url="http://localhost:8000/generate"
    )

    plfss_input_file = ((f"{DATA_FOLDER}/PLFSS_2024.json", 2024),)
    acronym_file = (f"{DATA_FOLDER}/acronym_mapping.xlsx",)

    preprocessor = PLFSSPreProcessor
    amendments_df = preprocessor.load_plfss_json(input_files=[plfss_input_file])
    acronym_mapping = preprocessor.load_acronyms_excel(acronym_file=acronym_file)

    amdt_summary_populator = AmendmentSummaryPopulator(
        llm_api_client=llm_api_client,
        amendments_df=amendments_df,
        acronym_mapping=acronym_mapping,
    )

    amendments_df = amdt_summary_populator.populate_summaries()


if __name__ == "__main__":
    main()
