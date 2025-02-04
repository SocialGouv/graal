import logging
import logging.config

import pandas as pd

from graal.custom_types import IntIndex, Prompt
from graal.summary.summary_generation_load_balancer import (
    SummaryGenerationLoadBalancer,
)
from graal.summary.summary_prompt_builder import SummaryPromptBuilder
from graal.utils.text_utils import SummaryTextNormalizer

logging.config.fileConfig("logging.conf")


class AmendmentSummarizer:
    def __init__(
        self,
        amendments_df: pd.DataFrame,
        summary_gen_load_balancer: SummaryGenerationLoadBalancer,
        config_prompt: Prompt,
        summary_column: str = "Objet amdt",
        base_linear_backoff_sec: int = 10,
    ):
        self.amendments_df = amendments_df
        self.summary_gen_load_balancer = summary_gen_load_balancer
        self.summary_column = summary_column
        self.config_prompt = config_prompt
        self.base_linear_backoff_sec = base_linear_backoff_sec
        self.row_to_amdt_idx = dict(enumerate(self.amendments_df["amdt_idx"]))
        self.amdt_idx_to_row = {v: k for k, v in self.row_to_amdt_idx.items()}

    def summarize(self, start_index: IntIndex, stop_index: IntIndex) -> pd.DataFrame:
        prompts = []
        amdt_indices = []

        for cur_row_index in range(start_index, stop_index + 1):
            amdt_idx = self.row_to_amdt_idx[cur_row_index]
            row = self.amendments_df.loc[
                self.amendments_df["amdt_idx"] == amdt_idx
            ].iloc[0]
            predefined_summary = self._get_predefined_summary(row)

            if predefined_summary:
                self._store_summary(amdt_idx, predefined_summary)
            else:
                if row["Exposé amdt"] and row["Corps amdt"]:
                    prompt = SummaryPromptBuilder.build_prompt_with_text_replacement(
                        config_prompt=self.config_prompt,
                        explanatory_statement=row["Exposé amdt"],
                        amdt_body=row["Corps amdt"],
                    )
                    prompts.append(prompt)
                    amdt_indices.append(amdt_idx)

        if prompts:
            summaries = self.summary_gen_load_balancer.generate_summaries_concurrent(
                prompts
            )
            summaries = self.summary_gen_load_balancer.rerun_long_results(
                summaries, max_words=25
            )
            for amdt_idx, summary in zip(amdt_indices, summaries):
                self._store_summary(amdt_idx, summary.strip())

        return self.amendments_df

    def _store_summary(self, amdt_idx: IntIndex, summary: str) -> None:
        self.amendments_df.loc[
            self.amendments_df["amdt_idx"] == amdt_idx, self.summary_column
        ] = summary

    def _get_predefined_summary(self, row: pd.Series) -> str:
        cleaned_explanatory_statement = SummaryTextNormalizer.normalize_text(
            row["Exposé amdt"]
        )
        cleaned_amdt_body = SummaryTextNormalizer.normalize_text(row["Corps amdt"])

        if (
            cleaned_explanatory_statement.startswith(
                SummaryTextNormalizer.normalize_text("Amendement rédactionnel.")
            )
            or cleaned_explanatory_statement.startswith(
                SummaryTextNormalizer.normalize_text("Rédactionnel.")
            )
            or SummaryTextNormalizer.normalize_text("correction d'erreur matérielle")
            in cleaned_explanatory_statement
            or SummaryTextNormalizer.normalize_text("amendement de précision")
            in cleaned_explanatory_statement
        ):
            return "Amendement rédactionnel."
        if cleaned_amdt_body.startswith(
            SummaryTextNormalizer.normalize_text("Supprimer cet article")
        ):
            return "Supprimer cet article."

        return ""
