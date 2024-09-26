import concurrent.futures
import logging
import time

import pandas as pd

from amendements_intelligents.summary.llm_clients import LLMAPIClient
from amendements_intelligents.summary.summary_prompt_builder import SummaryPromptBuilder
from amendements_intelligents.types import IntIndex
from amendements_intelligents.utils.text_utils import SummaryTextNormalizer


class AmendmentSummarizer:
    def __init__(
        self,
        amendments_df: pd.DataFrame,
        api_client: LLMAPIClient,
        summary_column: str = "Objet amdt",
        max_retries: int = 3,
        base_linear_backoff_sec: int = 10,
    ):
        self.amendments_df = amendments_df
        self.prompt_builder = SummaryPromptBuilder()
        self.api_client = api_client
        self.summary_column = summary_column
        self.max_retries = max_retries
        self.base_linear_backoff_sec = base_linear_backoff_sec
        # Create a mapping from row index to amdt_idx
        self.row_to_amdt_idx = dict(enumerate(self.amendments_df["amdt_idx"]))
        self.amdt_idx_to_row = {v: k for k, v in self.row_to_amdt_idx.items()}

    def summarize(
        self,
        start_index: IntIndex,
        stop_index: IntIndex,
        max_concurrent: int = 4,
    ) -> pd.DataFrame:
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=max_concurrent
        ) as executor:
            futures_to_amdt_idx: dict[concurrent.futures.Future, IntIndex] = {}

            cur_row_index = start_index
            for _ in range(max_concurrent):
                if (
                    cur_row_index >= len(self.amendments_df)
                    or cur_row_index > stop_index
                ):
                    break
                amdt_idx = self.row_to_amdt_idx[cur_row_index]
                self._submit_task_if_valid(amdt_idx, futures_to_amdt_idx, executor)
                cur_row_index += 1

            while True:
                if futures_to_amdt_idx:
                    completed_future = next(
                        concurrent.futures.as_completed(futures_to_amdt_idx)
                    )
                    try:
                        summary = completed_future.result(timeout=3 * 60)
                    except Exception as e:
                        amdt_idx = futures_to_amdt_idx.pop(completed_future)
                        logging.warning(f"Error for amdt_idx {amdt_idx}: {e}")
                        retries = getattr(completed_future, "retries", 0)
                        if retries < self.max_retries:
                            retries += 1
                            backoff_time = retries * self.base_linear_backoff_sec
                            logging.warning(
                                f"Retrying amdt_idx {amdt_idx} in {backoff_time} seconds... (Retry {retries}/{self.max_retries})"
                            )
                            time.sleep(backoff_time)
                            self._retry_task(
                                amdt_idx, retries, futures_to_amdt_idx, executor
                            )
                        else:
                            logging.warning(
                                f"Max retries reached for amdt_idx {amdt_idx}. Skipping..."
                            )
                        summary = ""
                    else:
                        amdt_idx = futures_to_amdt_idx.pop(completed_future)
                        if summary:
                            self.amendments_df.loc[
                                self.amendments_df["amdt_idx"] == amdt_idx,
                                self.summary_column,
                            ] = summary.strip()
                        logging.info(f"COMPLETED: amdt_idx {amdt_idx}")

                if (
                    cur_row_index < len(self.amendments_df)
                    and cur_row_index <= stop_index
                ):
                    amdt_idx = self.row_to_amdt_idx[cur_row_index]
                    self._submit_task_if_valid(amdt_idx, futures_to_amdt_idx, executor)
                    cur_row_index += 1

                if not futures_to_amdt_idx and (
                    cur_row_index >= len(self.amendments_df)
                    or cur_row_index > stop_index
                ):
                    break
        return self.amendments_df

    def _submit_task_if_valid(
        self,
        amdt_idx: IntIndex,
        futures_to_amdt_idx: dict[concurrent.futures.Future, IntIndex],
        executor: concurrent.futures.ThreadPoolExecutor,
    ) -> None:
        row = self.amendments_df[self.amendments_df["amdt_idx"] == amdt_idx].iloc[0]
        cleaned_explanatory_statement = SummaryTextNormalizer.normalize_text(
            row["Exposé amdt"]
        )
        cleaned_amdt_body = SummaryTextNormalizer.normalize_text(row["Corps amdt"])

        if cleaned_explanatory_statement != "" and cleaned_amdt_body != "":
            if cleaned_explanatory_statement.startswith(
                SummaryTextNormalizer.normalize_text("Amendement rédactionnel.")
            ):
                self.amendments_df.loc[
                    self.amendments_df["amdt_idx"] == amdt_idx, self.summary_column
                ] = "Amendement rédactionnel."
                logging.info(f'"Amendement rédactionnel." for amdt_idx {amdt_idx}')
                future = executor.submit(lambda x: x, "Amendement rédactionnel.")
                futures_to_amdt_idx[future] = amdt_idx
                return

            if cleaned_amdt_body.startswith(
                SummaryTextNormalizer.normalize_text("Supprimer cet article")
            ):
                self.amendments_df.loc[
                    self.amendments_df["amdt_idx"] == amdt_idx, self.summary_column
                ] = "Supprimer cet article"
                logging.info(f'"Supprimer cet article" for amdt_idx {amdt_idx}')
                future = executor.submit(lambda x: x, "Supprimer cet article")
                futures_to_amdt_idx[future] = amdt_idx
                return

            prompt = self.prompt_builder.build_prompt_new(
                explanatory_statement=row["Exposé amdt"],
                amdt_body=row["Corps amdt"],
            )
            future = executor.submit(self.api_client.generate_summary, prompt)
            futures_to_amdt_idx[future] = amdt_idx
            future.retries = 0
            logging.info(f"Submitted task for amdt_idx {amdt_idx}")

    def _retry_task(
        self,
        amdt_idx: IntIndex,
        retries: int,
        futures_to_amdt_idx: dict[concurrent.futures.Future, IntIndex],
        executor: concurrent.futures.ThreadPoolExecutor,
    ) -> None:
        row = self.amendments_df[self.amendments_df["amdt_idx"] == amdt_idx].iloc[0]
        prompt = self.prompt_builder.build_prompt_new(
            explanatory_statement=row["Exposé amdt"],
            amdt_body=row["Corps amdt"],
        )
        future = executor.submit(self.api_client.generate_summary, prompt)
        future.retries = retries
        futures_to_amdt_idx[future] = amdt_idx
        logging.info(
            f"Retrying task for amdt_idx {amdt_idx} (Retry {retries}/{self.max_retries})"
        )
