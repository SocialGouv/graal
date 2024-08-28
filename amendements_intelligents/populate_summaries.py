import os
import time

import pandas as pd

from amendements_intelligents.summary.amendment_summarizer import AmendmentSummarizer
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


class AmendmentSummaryPopulator:
    def __init__(
        self,
        acronym_mapping: dict[str, str],
        amendments_df: pd.DataFrame,
        llm_api_client: LLMAPIClient,
    ):
        self.acronym_mapping = acronym_mapping
        self.amendments_df = amendments_df
        self.llm_api_client = llm_api_client

    def populate_summaries(
        self,
    ) -> pd.DataFrame:
        preprocessor = PLFSSPreProcessor
        self.amendments_df = preprocessor.remap_columns_in_json_amendments(
            self.amendments_df
        )
        self.amendments_df = preprocessor.replace_acronyms(
            amendments_df=self.amendments_df,
            acronym_mapping=self.acronym_mapping,
            columns_to_normalize=["Exposé amdt", "Corps amdt"],
        )
        self.amendments_df = preprocessor.prepare_amendments_columns(
            amendments_df=self.amendments_df
        )
        self.amendments_df["Objet 70B()"] = ""

        summarizer = AmendmentSummarizer(self.amendments_df, self.llm_api_client)

        start_index = 0
        stop_index = self.amendments_df.shape[0]
        print(
            f"Starting to generate summaries for {stop_index - start_index + 1} amendments..."
        )
        start_time = time.time()
        amdt_with_summaries_df = summarizer.summarize(
            start_index=start_index,
            stop_index=stop_index,
        )

        # for i in range(start_index, stop_index):
        #     print(
        #         f'amdt_with_summaries_df {i}, {amdt_with_summaries_df.loc[i, "Num amdt"]}, "Objet 70B()": {amdt_with_summaries_df.loc[i, "Objet 70B()"]}\n'
        #     )

        end_time = time.time()
        print(f"Time taken: {end_time - start_time} seconds")

        return amdt_with_summaries_df


def main():
    # llm_api_client: LLMAPIClient = VllmAPIClient(MODEL_NAME, VLLM_ENDPOINT, USER, PASSWORD)
    # llm_api_client: LLMAPIClient = GroqAPIClient()
    llm_api_client: LLMAPIClient = LLMInferenceAPIClient(
        url="http://localhost:8000/generate"
    )
    plfss_input_file = (f"{DATA_FOLDER}/PLFSS_2024.json", 2024)
    acronym_file = f"{DATA_FOLDER}/acronym_mapping.xlsx"

    preprocessor = PLFSSPreProcessor
    amendments_df = preprocessor.load_plfss_json(input_files=[plfss_input_file])
    acronym_mapping = preprocessor.load_acronyms_excel(acronym_file=acronym_file)

    populator = AmendmentSummaryPopulator(
        llm_api_client=llm_api_client,
        amendments_df=amendments_df,
        acronym_mapping=acronym_mapping,
    )

    amdt_with_summaries_df = populator.populate_summaries()

    amdt_with_summaries_df.to_excel("data/amendments_with_summary.xlsx", index=False)


if __name__ == "__main__":
    main()
