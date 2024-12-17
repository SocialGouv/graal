import logging
import logging.config
import time
from typing import Optional

import pandas as pd

from graal.custom_types import Acronym, Prompt
from graal.summary.amendment_summarizer import AmendmentSummarizer
from graal.summary.summary_generation_load_balancer import (
    SummaryGenerationLoadBalancer,
)
from graal.utils.amendment_pre_processor import AmendmentPreProcessor

logging.config.fileConfig("logging.conf")


class SummaryHandler:
    def __init__(
        self,
        acronym_mapping: dict[Acronym, str],
        amendments_df: pd.DataFrame,
        summary_gen_load_balancer: SummaryGenerationLoadBalancer,
        config_prompt: Prompt,
        summary_column: str = "Objet amdt",
    ):
        self.acronym_mapping = acronym_mapping
        self.amendments_df = amendments_df
        self.summary_gen_load_balancer = summary_gen_load_balancer
        self.config_prompt = config_prompt
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
            config_prompt=self.config_prompt,
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

        end_time = time.time()
        logging.info(f"Time taken: {end_time - start_time} seconds")

        return amdt_with_summaries_df
