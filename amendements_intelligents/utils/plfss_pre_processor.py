import json
import logging

import pandas as pd
from pydantic import FilePath

from amendements_intelligents.types import ColumnName
from amendements_intelligents.utils.plfss_text_utils import (
    extract_plain_text_from_html,
    normalize_text,
)


class PLFSSPreProcessor:
    @staticmethod
    def load_plfss_json(input_files: list[tuple[FilePath, int]]) -> pd.DataFrame:
        dfs = []
        for file_name, year in input_files:
            with open(file_name, "r", encoding="utf-8-sig") as f:
                data = json.load(f)
            df = pd.DataFrame(data["amendements"])
            df["Year"] = year
            dfs.append(df)

        original_amendments_df = pd.concat(dfs, ignore_index=True)
        original_amendments_df["amdt_idx"] = range(len(original_amendments_df))
        return PLFSSPreProcessor.clean_up_json_columns(original_amendments_df)

    @staticmethod
    def load_acronyms_excel(acronym_file: FilePath) -> dict[str, str]:
        acronym_df = pd.read_excel(acronym_file)
        acronym_mapping = dict(zip(acronym_df["Acronyme"], acronym_df["Développement"]))
        return acronym_mapping

    @staticmethod
    def load_plfss_excel(input_file: FilePath) -> pd.DataFrame:
        return pd.read_excel(input_file)

    @staticmethod
    def clean_up_json_columns(amendements_df: pd.DataFrame) -> pd.DataFrame:
        amendements_df["Lecture"] = (
            amendements_df["chambre"].astype(str)
            + " "
            + amendements_df["legislature"].astype(str)
        )
        amendements_df["corps"] = amendements_df["corps"].apply(
            extract_plain_text_from_html
        )
        amendements_df["expose"] = amendements_df["expose"].apply(
            extract_plain_text_from_html
        )
        amendements_df["objet"] = amendements_df["objet"].apply(
            extract_plain_text_from_html
        )
        amendements_df["sort"] = amendements_df["sort"].apply(
            extract_plain_text_from_html
        )
        amendements_df["reponse"] = amendements_df["reponse"].apply(
            extract_plain_text_from_html
        )

        amendements_df["computed_batch"] = amendements_df["computed_batch"].apply(
            lambda x: ",".join(map(str, x))
        )
        return amendements_df

    @staticmethod
    def remap_columns_in_json_amendments(amendments_df: pd.DataFrame) -> pd.DataFrame:
        column_mapping = {
            "affectation_email": "Affectation (email)",
            "affectation_name": "Affectation (nom)",
            "article": "Num article",
            "computed_batch": "Allotissement",
            "corps": "Corps amdt",
            "expose": "Exposé amdt",
            "num": "Num amdt",
            "objet": "Objet",
            "organe": "Organe",
            "reponse": "Réponse",
            "sort": "Sort",
        }
        amendments_df.rename(columns=column_mapping, inplace=True)
        return amendments_df

    @staticmethod
    def clear_columns_to_be_overridden(
        amendments_df: pd.DataFrame, columns_to_clear: list[ColumnName]
    ) -> pd.DataFrame:
        for col_name in columns_to_clear:
            amendments_df[col_name] = None

        return amendments_df

    @staticmethod
    def handle_common_amendment_bodies(
        amendments_df: pd.DataFrame, amdt_bodies_column: str = "Corps amdt"
    ) -> pd.DataFrame:
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
            amendments_df[amdt_bodies_column]
            .str.contains(combined_pattern, regex=True)
            .fillna(False)
        )

        # Also append 'Num article' to small amendment bodies
        mask = mask | (amendments_df[amdt_bodies_column].str.len() < 50)
        logging.info(
            f'Appending {mask.sum()} "Num article" to small amendment bodies to get better clusters...\n'
        )

        # Concatenate the "Num article" to amdt_bodies_column for the masked rows
        amendments_df.loc[mask, amdt_bodies_column] = (
            amendments_df.loc[mask, amdt_bodies_column]
            + " "
            + amendments_df.loc[mask, "Num article"]
        )
        return amendments_df

    @staticmethod
    def handle_common_amendment_expose(
        amendments_df: pd.DataFrame,
        expose_column: str = "Exposé amdt",
        amdt_bodies_column: str = "Corps amdt",
    ) -> pd.DataFrame:
        """
        Concatenate expose_column with amdt_bodies_column if expose_column is:
        - Small (< 50 characters)
        - A common pattern (i.e. "Amendement rédactionnel.")
        """

        very_common_patterns = [
            "amendement rédactionnel",
        ]
        combined_pattern = "|".join(very_common_patterns)

        # Create mask with regex. It does not need to be an exact match
        mask = (
            amendments_df[expose_column]
            .str.contains(combined_pattern, regex=True, case=False)
            .fillna(False)
        )

        # Also append 'Num article' to small amendment bodies
        mask = mask | (amendments_df[expose_column].str.len() < 25)
        logging.info(
            f'Concatenating "{amdt_bodies_column}" to "{expose_column}" in {mask.sum()} amendements to get better clusters...\n'
        )

        amendments_df.loc[mask, expose_column] = (
            amendments_df.loc[mask, expose_column]
            + " "
            + amendments_df.loc[mask, amdt_bodies_column]
        )
        return amendments_df

    @staticmethod
    def remove_empty_rows_for_given_columns(
        amendments_df: pd.DataFrame,
        columns_to_filter_with: list[ColumnName],
    ) -> pd.DataFrame:
        for column in columns_to_filter_with:
            amendments_df.dropna(subset=column, inplace=True)
            amendments_df = amendments_df[
                amendments_df[column].str.strip().apply(len) > 0
            ].copy()
        return amendments_df

    @staticmethod
    def replace_acronyms(
        amendments_df: pd.DataFrame,
        acronym_mapping: dict[str, str],
        columns_to_normalize: list[ColumnName],
    ) -> pd.DataFrame:
        for column in columns_to_normalize:
            for acronym, full_name in acronym_mapping.items():
                amendments_df[column] = amendments_df[column].str.replace(
                    acronym, full_name, regex=True
                )
        return amendments_df

    @staticmethod
    def normalize_plfss(
        amendments_df: pd.DataFrame, columns_to_normalize: list[ColumnName]
    ) -> pd.DataFrame:
        for column in columns_to_normalize:
            amendments_df.loc[:, column] = amendments_df[column].apply(normalize_text)
        logging.info("PLFSS loaded for processing\n")

        return amendments_df
