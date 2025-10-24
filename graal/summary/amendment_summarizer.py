import logging
import logging.config

import pandas as pd

from graal.core.text_normalizers import TextNormalizerFactory
from graal.custom_types import IntIndex, Prompt
from graal.summary.summary_generation_load_balancer import (
    SummaryGenerationLoadBalancer,
)
from graal.summary.summary_prompt_builder import SummaryPromptBuilder

logging.config.fileConfig("logging.conf")


class AmendmentSummarizer:
    def __init__(
        self,
        amendments_df: pd.DataFrame,
        summary_gen_load_balancer: SummaryGenerationLoadBalancer,
        config_prompt: Prompt,
        should_overwrite: bool,
        summary_column: str = "Objet amdt",
        base_linear_backoff_sec: int = 10,
    ):
        self.amendments_df = amendments_df
        self.summary_gen_load_balancer = summary_gen_load_balancer
        self.summary_column = summary_column
        self.config_prompt = config_prompt
        self.base_linear_backoff_sec = base_linear_backoff_sec
        self.should_overwrite = should_overwrite
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

            # Skip rows that already have content in the summary column when should_overwrite is False
            current_summary = row[self.summary_column]
            if (
                not self.should_overwrite
                and pd.notna(current_summary)
                and current_summary.strip() != ""
            ):
                continue

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
            for amdt_idx, summary in zip(amdt_indices, summaries, strict=False):
                self._store_summary(amdt_idx, summary.strip())

        return self.amendments_df

    def _store_summary(self, amdt_idx: IntIndex, summary: str) -> None:
        self.amendments_df.loc[
            self.amendments_df["amdt_idx"] == amdt_idx, self.summary_column
        ] = summary

    def _get_predefined_summary(self, row: pd.Series) -> str:
        summary_normalizer = TextNormalizerFactory.get_normalizer("summary_generation")

        cleaned_explanatory_statement = summary_normalizer.normalize_for_feature(
            row["Exposé amdt"]
        )
        cleaned_amdt_body = summary_normalizer.normalize_for_feature(row["Corps amdt"])

        if (
            cleaned_explanatory_statement.startswith(
                summary_normalizer.normalize_for_feature("Amendement rédactionnel.")
            )
            or summary_normalizer.normalize_for_feature("amendement de précision")
            in cleaned_explanatory_statement
            or summary_normalizer.normalize_for_feature("amendement de correction")
            in cleaned_explanatory_statement
            or summary_normalizer.normalize_for_feature("amendement de clarification")
            in cleaned_explanatory_statement
            or summary_normalizer.normalize_for_feature("amendement de coordination")
            in cleaned_explanatory_statement
            or summary_normalizer.normalize_for_feature("amendement de suppression")
            in cleaned_explanatory_statement
            or summary_normalizer.normalize_for_feature(
                "correction d'erreur matérielle"
            )
            in cleaned_explanatory_statement
        ):
            return "Amendement rédactionnel."
        if cleaned_amdt_body.startswith(
            summary_normalizer.normalize_for_feature("Supprimer cet article")
        ):
            return "Supprimer cet article."

        return ""
