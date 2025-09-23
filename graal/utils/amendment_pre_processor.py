"""
This module provides utilities for preprocessing amendment data from JSON and Excel files.
It includes functions for loading, cleaning, and normalizing amendment data, as well as handling
common patterns in amendment bodies and exposes.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Iterable, Optional

import pandas as pd
from pydantic import FilePath
from unidecode import unidecode

from graal.custom_types import Acronym, ColumnName
from graal.utils.json_utils import load_json_from_file
from graal.utils.text_utils import extract_plain_text_from_html, normalize_text


class AmendmentPreProcessor:
    @staticmethod
    def load_amendments_json(
        input_files: list[FilePath], file_config: Optional[dict[FilePath, Any]] = None
    ) -> pd.DataFrame:
        df_accumulator = []
        # Initialize default_processing_timestamp before the loop to avoid warnings
        default_processing_timestamp = 0
        for file_name in input_files:
            data = load_json_from_file(str(file_name))
            df = pd.DataFrame(data["amendements"])

            if file_config:
                default_processing_timestamp = file_config[file_name][
                    "default_processing_timestamp"
                ]
                df["origin_project"] = file_config[file_name]["origin_project"]
            else:
                default_processing_timestamp = 0
                df["origin_project"] = "<Inconnue>"

            df["timestamp"] = df["date_derniere_modif"].apply(
                lambda x, default_ts=default_processing_timestamp: int(
                    datetime.strptime(x, "%Y-%m-%d %H:%M:%S.%f")
                    .replace(tzinfo=timezone.utc)
                    .timestamp()
                )
                if x not in [None, ""]
                else default_ts
            )

            df_accumulator.append(df)

        amendments_df = pd.concat(df_accumulator, ignore_index=True)
        amendments_df["amdt_idx"] = range(len(amendments_df))
        amendments_df = AmendmentPreProcessor.clean_up_json_columns(amendments_df)
        # Remap JSON column names to standard format
        amendments_df = AmendmentPreProcessor.remap_columns_in_json_amendments(
            amendments_df
        )
        return amendments_df

    @staticmethod
    def load_amendments_excel(
        input_files: list[FilePath], file_config: Optional[dict[FilePath, Any]] = None
    ) -> pd.DataFrame:
        df_accumulator = []
        default_processing_timestamp = 0
        for file_name in input_files:
            df = pd.read_excel(file_name)

            if file_config:
                default_processing_timestamp = file_config[file_name][
                    "default_processing_timestamp"
                ]
                df["origin_project"] = file_config[file_name]["origin_project"]
            else:
                default_processing_timestamp = 0
                df["origin_project"] = "<Inconnue>"

            df["timestamp"] = default_processing_timestamp

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
    def load_acronyms(config_df: pd.DataFrame) -> dict[Acronym, str]:
        acronym_mapping = dict(
            zip(config_df["Acronyme"], config_df["Développement"], strict=False)
        )
        return acronym_mapping

    @staticmethod
    def clean_up_json_columns(amendements_df: pd.DataFrame) -> pd.DataFrame:
        logging.debug(f"[JSON_CLEANUP] Starting with {len(amendements_df)} amendments")
        logging.debug(
            f"[JSON_CLEANUP] Available columns: {list(amendements_df.columns)}"
        )

        amendements_df["Lecture"] = (
            amendements_df["chambre"].astype(str)
            + " "
            + amendements_df["legislature"].astype(str)
        )

        # We need to have access to the HTML in some cases so we keep it in a new column
        amendements_df["Corps amdt original"] = amendements_df["corps"]

        # Log sample values before HTML extraction
        if "corps" in amendements_df.columns:
            sample_corps = amendements_df["corps"].head(3)
            for idx, value in sample_corps.items():
                logging.debug(f"[JSON_CLEANUP] Original corps[{idx}]: '{value}'")

        amendements_df["corps"] = amendements_df["corps"].apply(
            extract_plain_text_from_html
        )

        # Log sample values after HTML extraction
        if "corps" in amendements_df.columns:
            sample_corps = amendements_df["corps"].head(3)
            for idx, value in sample_corps.items():
                logging.debug(f"[JSON_CLEANUP] Cleaned corps[{idx}]: '{value}'")

        amendements_df["expose"] = amendements_df["expose"].apply(
            extract_plain_text_from_html
        )
        amendements_df["objet"] = amendements_df["objet"].apply(
            extract_plain_text_from_html
        )
        amendements_df["sort"] = amendements_df["sort"].apply(
            extract_plain_text_from_html
        )

        amendements_df["computed_batch"] = amendements_df["computed_batch"].apply(
            lambda x: ",".join(map(str, x))
        )

        logging.debug(f"[JSON_CLEANUP] Finished with {len(amendements_df)} amendments")
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
            "has_ever_been_on_dossier_de_banc": "A été dans le Dossier de Banc",
            "mission_titre_court": "Mission",
            "num": "Num amdt",
            "objet": "Objet amdt",
            "organe": "Organe",
            "pilot_entity": "Entité Pilote",
            "reponse": "Réponse",
            "sort": "Sort",
        }
        amendments_df.rename(columns=column_mapping, inplace=True)
        return amendments_df

    @staticmethod
    def clear_columns_to_be_overridden(
        amendments_df: pd.DataFrame, columns_to_clear: Iterable[ColumnName]
    ) -> pd.DataFrame:
        for col_name in columns_to_clear:
            logging.info(f"Clearing column {col_name}...\n")
            # Check if column exists and handle dtype compatibility
            if col_name in amendments_df.columns:
                # Convert to object dtype first to avoid dtype incompatibility warnings
                if amendments_df[col_name].dtype in [
                    "int64",
                    "int32",
                    "float64",
                    "float32",
                ]:
                    amendments_df[col_name] = amendments_df[col_name].astype("object")
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
        logging.debug(
            f"[AMENDMENT_PREPROCESSING] Processing {len(amendments_df)} amendments for common bodies"
        )

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

        # Log some examples before modification
        if mask.sum() > 0:
            examples = amendments_df.loc[
                mask, [amdt_bodies_column, "Num article"]
            ].head(3)
            for idx, row in examples.iterrows():
                logging.debug(
                    f"[AMENDMENT_PREPROCESSING] Before modification - Amendment {idx}: '{row[amdt_bodies_column]}' + '{row['Num article']}'"
                )

        # Concatenate the "Num article" to amdt_bodies_column for the masked rows
        amendments_df.loc[mask, amdt_bodies_column] = (
            amendments_df.loc[mask, amdt_bodies_column]
            + " "
            + amendments_df.loc[mask, "Num article"]
        )

        # Log some examples after modification
        if mask.sum() > 0:
            examples = amendments_df.loc[mask, amdt_bodies_column].head(3)
            for idx, text in examples.items():
                logging.debug(
                    f"[AMENDMENT_PREPROCESSING] After modification - Amendment {idx}: '{text}'"
                )

        return amendments_df

    @staticmethod
    def handle_common_amendment_expose_and_redactional(
        amendments_df: pd.DataFrame,
        expose_column: str = "Exposé amdt",
        amdt_bodies_column: str = "Corps amdt",
        add_redactional_column: bool = True,
    ) -> pd.DataFrame:
        """
        - Adds an 'is_redactional' column to identify redactional amendments.
        - Concatenates expose_column with amdt_bodies_column if expose_column is:
            - Small (< 50 characters)
            - A common pattern (i.e. "Amendement rédactionnel.")
        """

        # Use unidecode to make the pattern accent-insensitive
        erreur_mat_str = "correction d'erreur matérielle"
        redac_patterns = [
            rf"{unidecode(erreur_mat_str)}",
            rf"{unidecode('amendement rédactionnel')}",
            rf"{unidecode('amendement de précision')}",
            rf"{unidecode('amendement de correction')}",
            rf"{unidecode('amendement de clarification')}",
            rf"{unidecode('amendement de coordination')}",
            rf"{unidecode('amendement de suppression')}",
        ]
        combined_pattern = r"|".join(redac_patterns)

        expose_column_normalized = amendments_df[expose_column].apply(
            lambda x: unidecode(str(x).lower()) if pd.notnull(x) else x
        )

        if add_redactional_column:
            if expose_column in amendments_df.columns:
                amendments_df["is_redactional"] = expose_column_normalized.str.contains(
                    combined_pattern, regex=True, case=False
                ).fillna(False)
            else:
                amendments_df["is_redactional"] = False
            redactional_count = amendments_df["is_redactional"].sum()
            logging.info(f"Identified {redactional_count} redactional amendments.\n")

        # Concatenate expose_column with amdt_bodies_column for common/small exposes
        if (
            expose_column in amendments_df.columns
            and amdt_bodies_column in amendments_df.columns
        ):
            mask = expose_column_normalized.str.contains(
                combined_pattern, regex=True, case=False
            ).fillna(False)
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
    def drop_empty_rows_in_columns(
        amendments_df: pd.DataFrame,
        columns_to_filter: list[ColumnName],
    ) -> pd.DataFrame:
        """
        Drop rows where the specified columns are empty or contain only whitespace.
        """
        logging.debug(
            f"[DROP_EMPTY_ROWS] Starting with {len(amendments_df)} amendments"
        )
        logging.debug(f"[DROP_EMPTY_ROWS] Columns to filter: {columns_to_filter}")

        for column in columns_to_filter:
            initial_count = len(amendments_df)
            logging.debug(
                f"[DROP_EMPTY_ROWS] Processing column '{column}' - starting with {initial_count} amendments"
            )

            # Check if column exists
            if column not in amendments_df.columns:
                logging.error(
                    f"[DROP_EMPTY_ROWS] Column '{column}' does not exist! Available columns: {list(amendments_df.columns)}"
                )
                continue

            # Log some sample values before filtering
            sample_values = amendments_df[column].head(5)
            for idx, value in sample_values.items():
                logging.debug(
                    f"[DROP_EMPTY_ROWS] Sample value [{idx}]: '{value}' (type: {type(value)})"
                )

            # Count null values
            null_count = amendments_df[column].isnull().sum()
            logging.debug(
                f"[DROP_EMPTY_ROWS] Found {null_count} null values in column '{column}'"
            )

            # Drop null values
            amendments_df.dropna(subset=column, inplace=True)
            after_dropna_count = len(amendments_df)
            logging.debug(
                f"[DROP_EMPTY_ROWS] After dropping null values: {after_dropna_count} amendments ({initial_count - after_dropna_count} removed)"
            )

            # Count empty/whitespace-only values
            if len(amendments_df) > 0:
                empty_mask = amendments_df[column].str.strip().apply(len) == 0
                empty_count = empty_mask.sum()
                logging.debug(
                    f"[DROP_EMPTY_ROWS] Found {empty_count} empty/whitespace-only values in column '{column}'"
                )

                # Show examples of what will be removed
                if empty_count > 0:
                    empty_examples = amendments_df.loc[empty_mask, column].head(3)
                    for idx, value in empty_examples.items():
                        logging.debug(
                            f"[DROP_EMPTY_ROWS] Empty value example [{idx}]: '{value}'"
                        )

                amendments_df = amendments_df[
                    amendments_df[column].str.strip().apply(len) > 0
                ].copy()

            final_count = len(amendments_df)
            removed_count = initial_count - final_count
            logging.debug(
                f"[DROP_EMPTY_ROWS] After filtering column '{column}': {final_count} amendments ({removed_count} total removed)"
            )

            if final_count == 0:
                logging.error(
                    f"[DROP_EMPTY_ROWS] All amendments removed after filtering column '{column}'!"
                )
                break

        logging.debug(
            f"[DROP_EMPTY_ROWS] Final result: {len(amendments_df)} amendments"
        )
        return amendments_df

    @staticmethod
    def replace_acronyms(
        amendments_df: pd.DataFrame,
        acronym_mapping: dict[Acronym, str],
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
