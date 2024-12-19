import logging
import logging.config
import pickle  # nosec
import re
from itertools import cycle
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from graal.custom_types import (
    ColumnName,
    IntIndex,
    LLMName,
    LLMType,
    Prompt,
    RateLimitPerMinute,
)
from graal.summary.llm_clients import LLMAPIClient
from graal.summary.summary_prompt_builder import SummaryPromptBuilder
from graal.utils.rate_limiter import TokenBucketRateLimiter

logging.config.fileConfig("logging.conf")


class BlindEvalProject:
    def __init__(
        self,
        amendments_df: pd.DataFrame,
        metrics: list[ColumnName],
        rate_limiting_config: dict[LLMType, RateLimitPerMinute],
        config_prompt: Prompt,
    ):
        self.amendments_df = amendments_df
        self.metrics = metrics
        self.latest_gen_idx = 0
        self.data: dict[int, dict[str, Any]] = {}
        self.mapping_obj_to_author: dict[int, dict[str, str]] = {}
        self.shuffled_indices = np.random.permutation(len(self.amendments_df)).tolist()
        self.config_prompt = config_prompt
        self.rate_limiters = {
            type: TokenBucketRateLimiter(rate_limit)
            for type, rate_limit in rate_limiting_config.items()
        }

    def add_next_n_rows(self, n: int, llm_clients: dict[LLMName, LLMAPIClient]):
        all_llms = list(llm_clients.keys())
        np.random.shuffle(all_llms)

        # Create a cyclic iterator to ensure all sources are used evenly
        llm_cycle = cycle(all_llms)

        for _ in range(n):
            idx = self.shuffled_indices[self.latest_gen_idx]
            amendment = self.amendments_df.iloc[idx]

            clean_expert_summary = re.sub(
                r"\[sous-amendement\]|\*|REDACTIONNEL|Irr - |APPEL : |Appel -|IRR : ",
                "",
                amendment["Objet amdt"],
                flags=re.IGNORECASE,
            ).strip()

            prompt = SummaryPromptBuilder.build_prompt_with_text_replacement(
                config_prompt=self.config_prompt,
                explanatory_statement=amendment["Exposé amdt"],
                amdt_body=amendment["Corps amdt"],
            )

            llm_source = next(llm_cycle)
            llm_client = llm_clients[llm_source]
            if llm_client.type in self.rate_limiters:
                self.rate_limiters[llm_client.type].acquire()
            llm_summary = llm_client.generate_text(prompt)

            summaries = [(llm_summary, llm_source), (clean_expert_summary, "Expert")]
            np.random.shuffle(summaries)

            self.data[self.latest_gen_idx] = {
                "Objet 1": summaries[0][0],
                "Objet 2": summaries[1][0],
                "ID": self.latest_gen_idx,
                "Exposé amdt": amendment["Exposé amdt"],
                "Corps amdt": amendment["Corps amdt"],
            }

            for metric in self.metrics:
                self.data[self.latest_gen_idx][f"1 - {metric}"] = ""
                self.data[self.latest_gen_idx][f"2 - {metric}"] = ""
            self.mapping_obj_to_author[self.latest_gen_idx] = {
                "Objet 1": summaries[0][1],
                "Objet 2": summaries[1][1],
            }

            self.latest_gen_idx += 1

    def dump_to_disk(self, output_file: Path):
        with open(output_file, "wb") as f:
            pickle.dump(self, f)
            logging.info(f"Blind evaluation project saved to {output_file}")

    @classmethod
    def load_from_disk(cls, input_file: Path):
        with open(input_file, "rb") as f:
            return pickle.load(f)  # nosec

    def to_excel(
        self,
        output_file: Path,
        column_order: list[ColumnName],
        excluded_ids: list[IntIndex],
    ):
        df = pd.DataFrame.from_dict(self.data, orient="index")

        # Filter out rows where the "ID" column is 7 or 8
        df_filtered = df[~df["ID"].isin(excluded_ids)]

        # Write the DataFrame to an Excel file and freeze the top row
        with pd.ExcelWriter(output_file, engine="xlsxwriter") as writer:
            df_filtered[column_order].to_excel(
                writer, index=False, sheet_name="Évaluation à l'aveugle"
            )
            worksheet = writer.sheets["Évaluation à l'aveugle"]
            worksheet.freeze_panes(1, 0)
            # Set text wrap for all columns and set dark blue background for specific columns
            for col_num, col_name in enumerate(column_order):
                worksheet.write(
                    0,
                    col_num,
                    col_name,
                    writer.book.add_format(
                        {"font_size": 14, "bold": True, "font_name": "Cambria"}
                    ),
                )
                if col_name in ["Exposé amdt", "Corps amdt"]:
                    worksheet.set_column(
                        col_num,
                        col_num,
                        70,
                        writer.book.add_format(
                            {
                                "text_wrap": True,
                                "valign": "top",
                                "font_color": "#101b7e",
                            }
                        ),
                    )
                elif col_name in ["Objet 1", "Objet 2"]:
                    worksheet.set_column(
                        col_num,
                        col_num,
                        70,
                        writer.book.add_format(
                            {
                                "text_wrap": True,
                                "valign": "top",
                                "font_color": "#18671a",
                                "bold": True,
                            }
                        ),
                    )
                else:
                    worksheet.set_column(
                        col_num,
                        col_num,
                        17,
                        writer.book.add_format(
                            {
                                "text_wrap": True,
                                "valign": "top",
                                "align": "center",
                            }
                        ),
                    )
                    # Add data validation for dropdown menu with "oui" or "non"
                    for col_name in column_order:
                        if col_name not in [
                            "Exposé amdt",
                            "Corps amdt",
                            "Objet 1",
                            "Objet 2",
                        ]:
                            col_letter = chr(65 + column_order.index(col_name))
                            worksheet.data_validation(
                                f"{col_letter}2:{col_letter}{len(df_filtered) + 1}",
                                {
                                    "validate": "list",
                                    "source": ["oui", "non"],
                                    "input_message": "Choose 'oui' or 'non'",
                                    "error_message": "Invalid input, choose 'oui' or 'non'",
                                },
                            )
