import os
import time
from tracemalloc import start
from typing import Optional

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
        summary_column: str = "Objet",
    ):
        self.acronym_mapping = acronym_mapping
        self.amendments_df = amendments_df
        self.llm_api_client = llm_api_client
        self.summary_column = summary_column

    def populate_summaries(
        self,
        start_index: Optional[int] = None,
        stop_index: Optional[int] = None,
        max_concurrent: int = 4,
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
        self.amendments_df[self.summary_column] = ""

        summarizer = AmendmentSummarizer(
            self.amendments_df, self.llm_api_client, summary_column=self.summary_column
        )

        start_index = 0 if start_index is None else start_index
        stop_index = self.amendments_df.shape[0] if stop_index is None else stop_index
        print(
            f"Starting to generate summaries for {stop_index - start_index + 1} amendments..."
        )
        start_time = time.time()
        amdt_with_summaries_df = summarizer.summarize(
            start_index=start_index,
            stop_index=stop_index,
            max_concurrent=max_concurrent,
        )

        # for i in range(start_index, stop_index):
        #     print(
        #         f'amdt_with_summaries_df {i}, {amdt_with_summaries_df.loc[i, "Num amdt"]}, self.summary_column: {amdt_with_summaries_df.loc[i, self.summary_column]}\n'
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
        summary_column="Objet",
    )

    amdt_with_summaries_df = populator.populate_summaries(max_concurrent=2)

    amdt_with_summaries_df.to_excel(
        "data/amendments_with_summary_local.xlsx", index=False
    )


if __name__ == "__main__":
    main()
