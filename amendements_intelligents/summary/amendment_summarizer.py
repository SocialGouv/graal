import concurrent.futures
import logging
import time

import pandas as pd

from amendements_intelligents.summary.llm_clients import LLMAPIClient
from amendements_intelligents.summary.summary_prompt_builder import SummaryPromptBuilder
from amendements_intelligents.types import IntIndex
from amendements_intelligents.utils.plfss_text_utils import SummaryTextNormalizer


class AmendmentSummarizer:
    def __init__(
        self,
        amendments_df: pd.DataFrame,
        api_client: LLMAPIClient,
        summary_column: str = "Objet amdt",
        max_retries: int = 3,  # Maximum number of retries
        base_linear_backoff_sec: int = 10,  # Base backoff time in seconds
    ):
        self.amendments_df = amendments_df
        self.prompt_builder = SummaryPromptBuilder()
        self.api_client = api_client
        self.summary_column = summary_column
        self.max_retries = max_retries
        self.base_linear_backoff_sec = base_linear_backoff_sec

    def summarize(
        self,
        start_index: int,
        stop_index: int,
        max_concurrent: int = 4,
    ) -> pd.DataFrame:
        """
        Process amendments in the DataFrame by generating summaries for each amendment from start_index to stop_index (included).
        Calls to the LLM API are made concurrently using a ThreadPoolExecutor with a pool of size `max_concurrent`.
        """
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=max_concurrent
        ) as executor:
            futures_to_index: dict[concurrent.futures.Future, IntIndex] = {}

            cur_index = start_index
            # Submit initial batch of tasks
            for _ in range(max_concurrent):
                if cur_index >= self.amendments_df.shape[0] or cur_index > stop_index:
                    break
                self._submit_task_if_valid(cur_index, futures_to_index, executor)
                cur_index += 1

            # Process completed futures and submit new tasks as old ones complete
            while True:
                if futures_to_index:
                    completed_future = next(
                        concurrent.futures.as_completed(futures_to_index)
                    )
                    try:
                        summary = completed_future.result(timeout=3 * 60)
                    except Exception as e:
                        amdt_idx = futures_to_index.pop(completed_future)
                        logging.warning(f"Error for index {amdt_idx}: {e}")
                        retries = (
                            completed_future.retries
                            if hasattr(completed_future, "retries")
                            else 0
                        )
                        if retries < self.max_retries:
                            retries += 1
                            backoff_time = (
                                retries * self.base_linear_backoff_sec
                            )  # Linear backoff
                            logging.warning(
                                f"Retrying index {amdt_idx} in {backoff_time} seconds... (Retry {retries}/{self.max_retries})"
                            )
                            time.sleep(backoff_time)
                            self._retry_task(
                                amdt_idx, retries, futures_to_index, executor
                            )
                        else:
                            logging.warning(
                                f"Max retries reached for index {amdt_idx}. Skipping..."
                            )
                        summary = ""
                    else:
                        amdt_idx = futures_to_index.pop(completed_future)
                        if summary:
                            self.amendments_df.loc[
                                self.amendments_df["amdt_idx"] == amdt_idx,
                                self.summary_column,
                            ] = summary.strip()
                        logging.info(f"COMPLETED: {amdt_idx}")

                if cur_index < self.amendments_df.shape[0] and cur_index <= stop_index:
                    self._submit_task_if_valid(cur_index, futures_to_index, executor)
                    cur_index += 1

                if not futures_to_index and (
                    cur_index >= self.amendments_df.shape[0] or cur_index > stop_index
                ):
                    break
        return self.amendments_df

    def _submit_task_if_valid(
        self,
        index: int,
        futures_to_index: dict[concurrent.futures.Future, IntIndex],
        executor: concurrent.futures.ThreadPoolExecutor,
    ) -> None:
        """
        Helper method to submit a task to the executor if the amendment is valid, meaning that it doesn't start with "supprimer cet article" or is not empty.
        """
        row = self.amendments_df[self.amendments_df["amdt_idx"] == index].iloc[0]
        cleaned_explanatory_statement = SummaryTextNormalizer.normalize_text(
            row["Exposé amdt"]
        )
        cleaned_amdt_body = SummaryTextNormalizer.normalize_text(row["Corps amdt"])

        if cleaned_explanatory_statement != "" and cleaned_amdt_body != "":
            # Special case if row["Corps amdt"] starts with "supprimer cet article"
            if cleaned_amdt_body.startswith("supprimer cet article"):
                self.amendments_df.loc[
                    self.amendments_df["amdt_idx"] == index, self.summary_column
                ] = "Supprimer cet article"
                logging.info(f'"Supprimer cet article" for amdt_index {index}')
                future = executor.submit(lambda x: x, "Supprimer cet article")
                futures_to_index[future] = index
                return

            prompt = self.prompt_builder.build_prompt(
                explanatory_statement=row["Exposé amdt"],
                amdt_body=row["Corps amdt"],
            )
            # logging.info(f"prompt {prompt}")
            future = executor.submit(self.api_client.generate_summary, prompt)
            futures_to_index[future] = index
            future.retries = 0  # Initialize retries count
            logging.info(f"Submitted task for index {index}")

    def _retry_task(
        self,
        amdt_idx: int,
        retries: int,
        futures_to_index: dict[concurrent.futures.Future, IntIndex],
        executor: concurrent.futures.ThreadPoolExecutor,
    ) -> None:
        """
        Helper method to retry a task with a specified retry count.
        """
        row = self.amendments_df[self.amendments_df["amdt_idx"] == amdt_idx].iloc[0]
        prompt = self.prompt_builder.build_prompt(
            explanatory_statement=row["Exposé amdt"],
            amdt_body=row["Corps amdt"],
        )
        future = executor.submit(self.api_client.generate_summary, prompt)
        future.retries = retries  # Pass along the current retry count
        futures_to_index[future] = amdt_idx
        logging.info(
            f"Retrying task for index {amdt_idx} (Retry {retries}/{self.max_retries})"
        )
