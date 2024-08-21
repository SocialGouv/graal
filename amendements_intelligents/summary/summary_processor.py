import concurrent.futures

import pandas as pd

from amendements_intelligents.summary.summary_prompt_builder import SummaryPromptBuilder
from amendements_intelligents.summary.vllm_client import LLMApiClient
from amendements_intelligents.utils.plfss_text_utils import SummaryTextNormalizer


class AmendmentSummaryProcessor:
    def __init__(self, amendments_df: pd.DataFrame, api_client: LLMApiClient):
        self.amendments_df = amendments_df
        self.prompt_builder = SummaryPromptBuilder()
        self.api_client = api_client

    def process_amendments(
        self, stop_index: int, start_index: int = 0, max_concurrent: int = 8
    ) -> None:
        """
        Process amendments in the DataFrame by generating summaries for each amendment.
        Calls to the LLM API are made concurrently using a ThreadPoolExecutor with a pool of size `max_concurrent`.
        """
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=max_concurrent
        ) as executor:
            futures_to_index = {}

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
                    summary = completed_future.result()
                    index = futures_to_index.pop(completed_future)
                    self.amendments_df.loc[index, "Objet 70B()"] = summary
                    print(f"COMPLETED: {index}")

                if cur_index < self.amendments_df.shape[0] and cur_index <= stop_index:
                    self._submit_task_if_valid(cur_index, futures_to_index, executor)
                    cur_index += 1

                if not futures_to_index and (
                    cur_index >= self.amendments_df.shape[0] or cur_index > stop_index
                ):
                    break

    def _submit_task_if_valid(
        self,
        index: int,
        futures_to_index: dict,
        executor: concurrent.futures.ThreadPoolExecutor,
    ) -> None:
        """
        Helper method to submit a task to the executor if the amendment is valid, meaning that it doesn't start with "supprimer cet article" or is not empty.
        """
        row = self.amendments_df.iloc[index]
        cleaned_explanatory_statement = SummaryTextNormalizer.normalize_text(
            row["Exposé amdt"]
        )
        cleaned_amdt_body = SummaryTextNormalizer.normalize_text(row["Corps amdt"])

        if cleaned_explanatory_statement != "" and cleaned_amdt_body != "":
            # Special case if row["Corps amdt"] starts with "supprimer cet article"
            if cleaned_amdt_body.startswith("supprimer cet article"):
                self.amendments_df.loc[index, "Objet 70B()"] = "Supprimer cet article"
                print(f'"Supprimer cet article" for index {index}')
                future = executor.submit(lambda x: x, "Supprimer cet article")
                futures_to_index[future] = index
                return

            prompt = self.prompt_builder.build_prompt(
                explanatory_statement=row["Exposé amdt"],
                amdt_body=row["Corps amdt"],
            )
            # print(f"prompt {prompt}")
            future = executor.submit(self.api_client.generate_summary, prompt)
            futures_to_index[future] = index
            print(f"Submitted task for index {index}")
