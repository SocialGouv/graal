import json

import pandas as pd
from pydantic import FilePath

from amendements_intelligents.types import ColumnName
from amendements_intelligents.utils.text_utils import (
    extract_plain_text_from_html,
    normalize_text,
)


class PLFSSDataProcessor:
    def __init__(self, input_file: FilePath):
        self.input_file = input_file
        self.amendments_df = None

    def load_plfss(self) -> None:
        with open(self.input_file, "r", encoding="utf-8-sig") as file:
            data = json.load(file)
        self.amendments_df = pd.DataFrame(data["amendements"])
        self.amendments_df["Lecture"] = (
            self.amendments_df["chambre"].astype(str)
            + " "
            + self.amendments_df["legislature"].astype(str)
        )
        self.amendments_df["corps"] = self.amendments_df["corps"].apply(
            extract_plain_text_from_html
        )
        self.amendments_df["expose"] = self.amendments_df["expose"].apply(
            extract_plain_text_from_html
        )
        self.amendments_df["sort"] = self.amendments_df["sort"].apply(
            extract_plain_text_from_html
        )
        self.amendments_df["reponse"] = self.amendments_df["reponse"].apply(
            extract_plain_text_from_html
        )

        column_mapping = {
            "computed_batch": "Allotissement",
            "num": "Num amdt",
            "corps": "Corps amdt",
            "expose": "Exposé amdt",
            "sort": "Sort",
            "reponse": "Réponse",
            "article": "Num article",
        }
        self.amendments_df.rename(columns=column_mapping, inplace=True)
        self.amendments_df["Allotissement"] = None

        self.preprocessed_amendments_df = self.amendments_df.copy()

    def _handle_common_amendment_bodies(self) -> None:
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
            self.preprocessed_amendments_df["Corps amdt"]
            .str.contains(combined_pattern, regex=True)
            .fillna(False)
        )

        # Also append 'Num article' to small amendment bodies
        mask = mask | (self.preprocessed_amendments_df["Corps amdt"].str.len() < 50)
        print(
            f'Appending {mask.sum()} "Num article" to small amendment bodies to get better clusters...\n'
        )

        # Concatenate the "Num article" to "Corps amdt" for the masked rows
        self.preprocessed_amendments_df.loc[mask, "Corps amdt"] = (
            self.preprocessed_amendments_df.loc[mask, "Corps amdt"]
            + " "
            + self.preprocessed_amendments_df.loc[mask, "Num article"]
        )

    def _remove_empty_rows_for_given_columns(
        self,
        columns_to_filter_with: list[ColumnName] = ["Corps amdt"],
    ) -> None:
        for column in columns_to_filter_with:
            self.preprocessed_amendments_df.dropna(subset=column, inplace=True)
            self.preprocessed_amendments_df = self.preprocessed_amendments_df[
                self.preprocessed_amendments_df[column].str.strip().apply(len) > 0
            ]

    def preprocess_plfss(self) -> pd.DataFrame:
        columns_to_filter_with = ["Corps amdt"]
        self._remove_empty_rows_for_given_columns(
            columns_to_filter_with=columns_to_filter_with,
        )
        self._handle_common_amendment_bodies()
        for column in columns_to_filter_with:
            self.preprocessed_amendments_df[column] = self.preprocessed_amendments_df[
                column
            ].apply(normalize_text)
        print("PLFSS loaded for processing\n")

        return self.preprocessed_amendments_df
