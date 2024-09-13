import logging
import logging.config
import os
import time
from typing import Optional

import pandas as pd

from amendements_intelligents.summary.amendment_summarizer import AmendmentSummarizer
from amendements_intelligents.summary.llm_clients import FakeLLMAPIClient, LLMAPIClient
from amendements_intelligents.utils.amendment_pre_processor import AmendmentPreProcessor

logging.config.fileConfig("logging.conf")


class SummaryPopulator:
    def __init__(
        self,
        acronym_mapping: dict[str, str],
        amendments_df: pd.DataFrame,
        llm_api_client: LLMAPIClient,
        summary_column: str = "Objet amdt",
    ):
        self.acronym_mapping = acronym_mapping
        self.amendments_df = amendments_df
        self.llm_api_client = llm_api_client
        self.summary_column = summary_column

    def preprocess(self) -> pd.DataFrame:
        self.amendments_df = AmendmentPreProcessor.remap_columns_in_json_amendments(
            self.amendments_df
        )
        self.amendments_df = AmendmentPreProcessor.replace_acronyms(
            amendments_df=self.amendments_df,
            acronym_mapping=self.acronym_mapping,
            columns_to_normalize=["Exposé amdt", "Corps amdt"],
        )
        self.amendments_df = AmendmentPreProcessor.clear_columns_to_be_overridden(
            amendments_df=self.amendments_df, columns_to_clear=[self.summary_column]
        )
        self.amendments_df[self.summary_column] = ""
        return self.amendments_df

    def populate(
        self,
        start_index: Optional[int] = None,
        stop_index: Optional[int] = None,
        max_concurrent: int = 4,
    ) -> pd.DataFrame:
        summarizer = AmendmentSummarizer(
            self.amendments_df, self.llm_api_client, summary_column=self.summary_column
        )

        start_index = 0 if start_index is None else start_index
        stop_index = self.amendments_df.shape[0] if stop_index is None else stop_index
        logging.info(
            f"Starting to generate summaries for {stop_index - start_index + 1} amendments..."
        )
        start_time = time.time()
        amdt_with_summaries_df = summarizer.summarize(
            start_index=start_index,
            stop_index=stop_index,
            max_concurrent=max_concurrent,
        )

        # for i in range(start_index, stop_index):
        #     logging.info(
        #         f'amdt_with_summaries_df {i}, {amdt_with_summaries_df.loc[i, "Num amdt"]}, self.summary_column: {amdt_with_summaries_df.loc[i, self.summary_column]}\n'
        #     )

        end_time = time.time()
        logging.info(f"Time taken: {end_time - start_time} seconds")

        return amdt_with_summaries_df


def main():
    DATA_FOLDER = os.getenv("DATA_FOLDER")
    # MODEL_NAME = os.getenv("MODEL_NAME")
    # LLM_ENDPOINT = os.getenv("LLM_ENDPOINT")
    # USER = os.getenv("USER")
    # PASSWORD = os.getenv("PASSWORD")
    # llm_api_client: LLMAPIClient = LLMInferenceAPIClient(
    #     url=LLM_ENDPOINT,
    #     auth=(USER, PASSWORD),
    # )
    # llm_api_client: LLMAPIClient = VllmAPIClient(MODEL_NAME, VLLM_ENDPOINT, USER, PASSWORD)
    # llm_api_client: LLMAPIClient = GroqAPIClient()
    llm_api_client: LLMAPIClient = FakeLLMAPIClient()

    input_file = (f"{DATA_FOLDER}/PLFSS_2024.json", 2024)
    acronym_file = f"{DATA_FOLDER}/acronym_mapping.xlsx"

    amendments_df = AmendmentPreProcessor.load_amendments_json(input_files=[input_file])
    acronym_mapping = AmendmentPreProcessor.load_acronyms_excel(
        acronym_file=acronym_file
    )

    amdt_summary_populator = SummaryPopulator(
        llm_api_client=llm_api_client,
        amendments_df=amendments_df,
        acronym_mapping=acronym_mapping,
        summary_column="Objet amdt",
    )

    amdt_summary_populator.preprocess()

    amdt_with_summaries_df = amdt_summary_populator.populate(max_concurrent=2)

    amdt_with_summaries_df.to_excel(
        "data/amendments_with_summary_local.xlsx", index=False
    )


if __name__ == "__main__":
    main()
