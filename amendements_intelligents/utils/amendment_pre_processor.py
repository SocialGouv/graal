"""
This module provides utilities for preprocessing amendment data from JSON and Excel files.
It includes functions for loading, cleaning, and normalizing amendment data, as well as handling
common patterns in amendment bodies and exposes.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional

import pandas as pd
from pydantic import FilePath

from amendements_intelligents.types import ColumnName
from amendements_intelligents.utils.text_utils import (
    extract_plain_text_from_html,
    normalize_text,
)


class AmendmentPreProcessor:
    @staticmethod
    def load_amendments_json(
        input_files: list[FilePath], file_config: Optional[dict[FilePath, Any]] = None
    ) -> pd.DataFrame:
        df_accumulator = []
        # Initialize default_timestamp before the loop to avoid warnings
        default_timestamp = 0
        for file_name in input_files:
            with open(file_name, "r", encoding="utf-8-sig") as f:
                data = json.load(f)
            df = pd.DataFrame(data["amendements"])

            if file_config:
                default_timestamp = file_config[file_name]["default_timestamp"]
                df["origin_project"] = file_config[file_name]["origin_project"]
            else:
                default_timestamp = 0
                df["origin_project"] = "<Inconnue>"

            df["timestamp"] = df["date_derniere_modif"].apply(
                lambda x: int(
                    datetime.strptime(x, "%Y-%m-%d %H:%M:%S.%f")
                    .replace(tzinfo=timezone.utc)
                    .timestamp()
                )
                if x not in [None, ""]
                else default_timestamp
            )

            df_accumulator.append(df)

        amendments_df = pd.concat(df_accumulator, ignore_index=True)
        amendments_df["amdt_idx"] = range(len(amendments_df))
        return AmendmentPreProcessor.clean_up_json_columns(amendments_df)

    @staticmethod
    def load_amendments_excel(
        input_files: list[FilePath], file_config: Optional[dict[FilePath, Any]] = None
    ) -> pd.DataFrame:
        df_accumulator = []
        default_timestamp = 0
        for file_name in input_files:
            df = pd.read_excel(file_name)

            if file_config:
                default_timestamp = file_config[file_name]["default_timestamp"]
                df["origin_project"] = file_config[file_name]["origin_project"]
            else:
                default_timestamp = 0
                df["origin_project"] = "<Inconnue>"

            df["timestamp"] = default_timestamp

            df_accumulator.append(df)

        amendments_df = pd.concat(df_accumulator, ignore_index=True)
        amendments_df["amdt_idx"] = range(len(amendments_df))
        return amendments_df

    @staticmethod
    def concatenate_dataframes(df1: pd.DataFrame, df2: pd.DataFrame) -> pd.DataFrame:
        if not df1.empty:
            max_amdt_idx = df1["amdt_idx"].max() + 1
        else:
            max_amdt_idx = 0

        df2["amdt_idx"] += max_amdt_idx

        # Ensure both dataframes have the same columns
        for column in df1.columns.difference(df2.columns):
            df2[column] = None
        for column in df2.columns.difference(df1.columns):
            df1[column] = None

        concatenated_df = pd.concat([df1, df2], ignore_index=True)
        return concatenated_df

    @staticmethod
    def load_acronyms(acronym_df: pd.DataFrame) -> dict[str, str]:
        acronym_mapping = dict(zip(acronym_df["Acronyme"], acronym_df["Développement"]))
        return acronym_mapping

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
            "avis": "Avis du Gouvernement",
            "computed_batch": "Allotissement",
            "corps": "Corps amdt",
            "expose": "Exposé amdt",
            "groupe": "Groupe",
            "num": "Num amdt",
            "objet": "Objet amdt",
            "organe": "Organe",
            "reponse": "Réponse",
            "sort": "Sort",
            "has_ever_been_on_dossier_de_banc": "A été dans le Dossier de Banc",
        }
        amendments_df.rename(columns=column_mapping, inplace=True)
        return amendments_df

    @staticmethod
    def clear_columns_to_be_overridden(
        amendments_df: pd.DataFrame, columns_to_clear: list[ColumnName]
    ) -> pd.DataFrame:
        for col_name in columns_to_clear:
            logging.info(f"Clearing column {col_name}...\n")
            amendments_df.loc[:, col_name] = None

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

        amendments_df[amdt_bodies_column] = amendments_df[
            amdt_bodies_column
        ].str.replace(
            r"supprimer l'article liminaire\.?",
            "Supprimer cet article.",
            regex=True,
            case=False,
        )

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
        mask = mask | (amendments_df[expose_column].str.len() < 50)
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
    def normalize_amendments(
        amendments_df: pd.DataFrame, columns_to_normalize: list[ColumnName]
    ) -> pd.DataFrame:
        for column in columns_to_normalize:
            amendments_df.loc[:, column] = amendments_df[column].apply(normalize_text)
            logging.info(f'Column "{column}" normalized.\n')

        return amendments_df
