import json

import pandas as pd
from pydantic import FilePath

from amendements_intelligents.types import ColumnName
from amendements_intelligents.utils.plfss_text_utils import (
    extract_plain_text_from_html,
    normalize_text,
)


class PLFSSPreProcessor:
    def __init__(self):
        self.original_amendments_df = None
        self.work_amendments_df = None

    def load_plfss_json(self, input_files: list[FilePath]) -> None:
        dfs = []
        for file in input_files:
            with open(file, "r", encoding="utf-8-sig") as f:
                data = json.load(f)
            df = pd.DataFrame(data["amendements"])
            dfs.append(df)

        self.original_amendments_df = pd.concat(dfs, ignore_index=True)
        self.clean_up_json_columns()

    def load_plfss_excel(self, input_file: FilePath) -> None:
        self.original_amendments_df = pd.read_excel(input_file)

    def clean_up_json_columns(self) -> pd.DataFrame:
        self.original_amendments_df["Lecture"] = (
            self.original_amendments_df["chambre"].astype(str)
            + " "
            + self.original_amendments_df["legislature"].astype(str)
        )
        self.original_amendments_df["corps"] = self.original_amendments_df[
            "corps"
        ].apply(extract_plain_text_from_html)
        self.original_amendments_df["expose"] = self.original_amendments_df[
            "expose"
        ].apply(extract_plain_text_from_html)
        self.original_amendments_df["sort"] = self.original_amendments_df["sort"].apply(
            extract_plain_text_from_html
        )
        self.original_amendments_df["reponse"] = self.original_amendments_df[
            "reponse"
        ].apply(extract_plain_text_from_html)

        self.original_amendments_df["computed_batch"] = self.original_amendments_df[
            "computed_batch"
        ].apply(lambda x: ",".join(map(str, x)))
        return self.original_amendments_df

    def remap_columns_in_json_amendments(self) -> pd.DataFrame:
        column_mapping = {
            "affectation_email": "Affectation (email)",
            "affectation_name": "Affectation (nom)",
            "article": "Num article",
            "computed_batch": "Allotissement",
            "corps": "Corps amdt",
            "expose": "Exposé amdt",
            "num": "Num amdt",
            "reponse": "Réponse",
            "sort": "Sort",
        }
        self.original_amendments_df.rename(columns=column_mapping, inplace=True)
        return self.original_amendments_df

    def prepare_work_amendments_df(self) -> pd.DataFrame:
        self.original_amendments_df["Affectation (email)"] = None
        self.original_amendments_df["Affectation (nom)"] = None
        self.original_amendments_df["Allotissement"] = None
        self.original_amendments_df["Corps amdt orig"] = self.original_amendments_df[
            "Corps amdt"
        ]
        self.original_amendments_df["Exposé amdt orig"] = self.original_amendments_df[
            "Exposé amdt"
        ]

        self.work_amendments_df = self.original_amendments_df.copy()
        return self.work_amendments_df

    def handle_common_amendment_bodies(self) -> None:
        """
        Append 'Num article' to :
        - Small amendment bodies
        - Amendment bodies that mention suppression of an article, a paragraph or a range of paragraphs

        Otherwise they are not discriminative enough.
        """

        very_common_patterns = [
            "Supprimer cet article\\.?",
            "Supprimer l(?:'|’)alinéa \\d{1,5}\\.?",
            "Supprimer les alinéas \\d{1,5} (?:à|et) \\d{1,5}\\.?",
        ]
        combined_pattern = "|".join(very_common_patterns)

        # Create mask with regex. It does not need to be an exact match
        mask = (
            self.work_amendments_df["Corps amdt"]
            .str.contains(combined_pattern, regex=True)
            .fillna(False)
        )

        # Also append 'Num article' to small amendment bodies
        mask = mask | (self.work_amendments_df["Corps amdt"].str.len() < 50)
        print(
            f'Appending {mask.sum()} "Num article" to small amendment bodies to get better clusters...\n'
        )

        # Concatenate the "Num article" to "Corps amdt" for the masked rows
        self.work_amendments_df.loc[mask, "Corps amdt"] = (
            self.work_amendments_df.loc[mask, "Corps amdt"]
            + " "
            + self.work_amendments_df.loc[mask, "Num article"]
        )
        return self.work_amendments_df

    def handle_common_amendment_expose(self) -> None:
        """
        Concatenate Exposé amdt with Corps amdt if Exposé amdt is:
        - Small (< 50 characters)
        - A common pattern (i.e. "Amendement rédactionnel.")
        """

        very_common_patterns = [
            "amendement rédactionnel",
        ]
        combined_pattern = "|".join(very_common_patterns)

        # Create mask with regex. It does not need to be an exact match
        mask = (
            self.work_amendments_df["Exposé amdt"]
            .str.contains(combined_pattern, regex=True, case=False)
            .fillna(False)
        )

        # Also append 'Num article' to small amendment bodies
        mask = mask | (self.work_amendments_df["Exposé amdt"].str.len() < 25)
        print(
            f"Concatenating Corps Amdt to Exposé amdt in {mask.sum()} amendements to get better clusters...\n"
        )

        self.work_amendments_df.loc[mask, "Exposé amdt"] = (
            self.work_amendments_df.loc[mask, "Exposé amdt"]
            + " "
            + self.work_amendments_df.loc[mask, "Corps amdt"]
        )
        return self.work_amendments_df

    def remove_empty_rows_for_given_columns(
        self,
        columns_to_filter_with: list[ColumnName],
    ) -> None:
        for column in columns_to_filter_with:
            self.work_amendments_df.dropna(subset=column, inplace=True)
            self.work_amendments_df = self.work_amendments_df[
                self.work_amendments_df[column].str.strip().apply(len) > 0
            ]
        return self.work_amendments_df

    def normalize_plfss(self, columns_to_normalize: list[ColumnName]) -> pd.DataFrame:
        for column in columns_to_normalize:
            self.work_amendments_df[column] = self.work_amendments_df[column].apply(
                normalize_text
            )
        print("PLFSS loaded for processing\n")

        return self.work_amendments_df
