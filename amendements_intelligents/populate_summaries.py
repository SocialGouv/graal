import logging
import logging.config
import os
import time
from typing import Optional

import pandas as pd

from amendements_intelligents.summary.amendment_summarizer import AmendmentSummarizer
from amendements_intelligents.summary.llm_clients import (
    AlbertAPIClient,
    FakeLLMAPIClient,
    LLMAPIClient,
    OllamaAPIClient,
)
from amendements_intelligents.summary.summary_generation_load_balancer import (
    SummaryGenerationLoadBalancer,
)
from amendements_intelligents.utils.amendment_pre_processor import AmendmentPreProcessor

logging.config.fileConfig("logging.conf")


class SummaryHandler:
    def __init__(
        self,
        acronym_mapping: dict[str, str],
        amendments_df: pd.DataFrame,
        summary_gen_load_balancer: SummaryGenerationLoadBalancer,
        summary_column: str = "Objet amdt",
    ):
        self.acronym_mapping = acronym_mapping
        self.amendments_df = amendments_df
        self.summary_gen_load_balancer = summary_gen_load_balancer
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
    ) -> pd.DataFrame:
        summarizer = AmendmentSummarizer(
            amendments_df=self.amendments_df,
            summary_gen_load_balancer=self.summary_gen_load_balancer,
            summary_column=self.summary_column,
        )

        start_index = 0 if start_index is None else start_index
        stop_index = (
            self.amendments_df.shape[0] - 1 if stop_index is None else stop_index
        )
        logging.info(
            f"Starting to generate summaries for {stop_index - start_index + 1} amendments..."
        )
        start_time = time.time()
        amdt_with_summaries_df = summarizer.summarize(
            start_index=start_index,
            stop_index=stop_index,
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

    albert_api_client: LLMAPIClient = AlbertAPIClient(
        base_url="https://albert.api.etalab.gouv.fr/v1",
        api_key=os.getenv("ETALAB_API_KEY"),
        model_name="meta-llama/Meta-Llama-3.1-70B-Instruct",
    )
    # fake_api_client: LLMAPIClient = FakeLLMAPIClient()
    OLLAMA_USER = os.getenv("OLLAMA_USER")
    OLLAMA_PASSWORD = os.getenv("OLLAMA_PASSWORD")
    OLLAMA_ENDPOINT = os.getenv("OLLAMA_ENDPOINT")
    OLLAMA_MODEL_NAME = os.getenv("OLLAMA_MODEL_NAME")
    logging.info(
        f"{OLLAMA_USER}, {OLLAMA_PASSWORD}, {OLLAMA_ENDPOINT}, {OLLAMA_MODEL_NAME}"
    )
    ollama_api_client = OllamaAPIClient(
        endpoint=OLLAMA_ENDPOINT,
        model_name=OLLAMA_MODEL_NAME,
        user=OLLAMA_USER,
        password=OLLAMA_PASSWORD,
    )
    summary_gen_load_balancer = SummaryGenerationLoadBalancer(
        clients=[albert_api_client, ollama_api_client], queue_timeout=4
    )

    INPUT_FILE = f"{DATA_FOLDER}/input_plfss/lecture-an-17-325-PO59048.json"
    acronym_file = f"{DATA_FOLDER}/acronym_mapping.xlsx"

    amendments_df = AmendmentPreProcessor.load_amendments_json(input_files=[INPUT_FILE])
    acronym_mapping = AmendmentPreProcessor.load_acronyms_excel(
        acronym_file=acronym_file
    )

    amdt_summary_populator = SummaryHandler(
        summary_gen_load_balancer=summary_gen_load_balancer,
        amendments_df=amendments_df,
        acronym_mapping=acronym_mapping,
        summary_column="Objet amdt",
    )

    amdt_summary_populator.preprocess()

    amdt_with_summaries_df = amdt_summary_populator.populate()

    amdt_with_summaries_df.to_excel(
        "data/amendments_with_summary_local.xlsx", index=False
    )


if __name__ == "__main__":
    main()
