import logging
import logging.config

import pandas as pd

from graal.custom_types import LegalDocumentType, PLFProgramName, UserName
from graal.utils.text_utils import AttributionTextNormalizer

logging.config.fileConfig("logging.conf")
logger = logging.getLogger(__name__)


class AttributionDataLoader:
    @staticmethod
    def load_codes_and_articles(excel_data: dict) -> pd.DataFrame:
        """Load and normalize codes and articles from the data."""
        return AttributionDataLoader.load_articles_by_type(
            excel_data, LegalDocumentType.CODE.value
        )

    @staticmethod
    def load_laws_and_articles(excel_data: dict) -> pd.DataFrame:
        """Load and normalize laws and articles from the data."""
        return AttributionDataLoader.load_articles_by_type(
            excel_data, LegalDocumentType.LAW.value
        )

    @staticmethod
    def load_ordonnances_and_articles(excel_data: dict) -> pd.DataFrame:
        """Load and normalize ordonnances and articles from the data."""
        return AttributionDataLoader.load_articles_by_type(
            excel_data, LegalDocumentType.ORDONNANCE.value
        )

    @staticmethod
    def load_articles_by_type(excel_data: dict, article_type: str) -> pd.DataFrame:
        """Load and normalize articles by type from the data."""
        articles_df = excel_data["Code et Article"].copy()
        articles_df["Type"] = articles_df["Type"].str.lower()
        articles_df = articles_df[
            articles_df["Type"].str.contains(article_type, na=False)
        ]
        articles_df.loc[:, "Articles"] = articles_df["Articles"].apply(
            lambda x: AttributionTextNormalizer.normalize_text(str(x))
        )
        articles_df.loc[:, "Valeur"] = articles_df["Valeur"].apply(
            lambda x: AttributionTextNormalizer.normalize_text(str(x))
        )
        articles_df.rename(
            columns={"Prénom Nom": "Affectation (nom)", "Valeur": "value"}, inplace=True
        )
        return articles_df

    @staticmethod
    def load_programs(config_excel: dict) -> dict[PLFProgramName, UserName]:
        program_to_attribution: dict[PLFProgramName, UserName] = {}
        # Load program mappings from config if available
        if "Responsables de programme" in config_excel:
            programs_df = config_excel["Responsables de programme"]
            for _, row in programs_df.iterrows():
                if pd.notna(row["Programme budgétaire"]) and pd.notna(
                    row["Prénom Nom"]
                ):
                    program = AttributionTextNormalizer.normalize_text(
                        row["Programme budgétaire"]
                    )
                    program_to_attribution[program] = row["Prénom Nom"]
        return program_to_attribution

    @staticmethod
    def load_keywords(
        excel_data: dict, acronym_mapping: dict[str, str]
    ) -> pd.DataFrame:
        """Load and normalize keywords from the data."""
        keywords_df = excel_data["Mots clés"]

        # Stage 1: Replace acronyms based on the acronym_mapping
        def replace_acronyms(text: str, mapping: dict[str, str]) -> str:
            for key, value in mapping.items():
                text = text.replace(key, value)
            return text

        keywords_df["Mots clés"] = keywords_df["Mots clés"].apply(
            lambda x: replace_acronyms(str(x), acronym_mapping)
        )

        # Stage 2: Normalize the text after replacing acronyms
        keywords_df["Mots clés"] = keywords_df["Mots clés"].apply(
            lambda x: AttributionTextNormalizer.normalize_text(str(x))
        )

        # Rename column
        keywords_df.rename(columns={"Prénom Nom": "Affectation (nom)"}, inplace=True)

        return keywords_df

    @staticmethod
    def load_name_to_user_info_mappings(excel_data: dict) -> dict[str, dict[str, str]]:
        """Load name and user info (email, entité pilote) mappings from the "Infos Agents" sheet."""
        user_info_df = excel_data["Infos Agents"]
        user_info_df.fillna("", inplace=True)
        # Check for duplicated "Prénom Nom" values and log a warning
        duplicated_names = user_info_df[
            user_info_df.duplicated(subset=["Prénom Nom"], keep=False)
        ]
        if not duplicated_names.empty:
            logger.warning(
                f"Warning: Duplicated 'Prénom Nom' values found: {duplicated_names['Prénom Nom'].unique()}"
            )

        # Drop duplicates, keeping the first instance
        user_info_df = user_info_df.drop_duplicates(subset=["Prénom Nom"], keep="first")

        user_info_mappings = user_info_df.set_index("Prénom Nom")[
            ["Mail", "Entité Pilote"]
        ].to_dict(orient="index")
        return user_info_mappings

    @staticmethod
    def load_default_attribution_mappings(excel_data: dict) -> list[str]:
        """Load default attribution mappings from the "Attribution par défaut" sheet. Used when no other attribution is found."""
        attribution_mappings_when_empty = excel_data["Attribution par défaut"][
            "Prénom Nom"
        ].tolist()
        return attribution_mappings_when_empty

    @staticmethod
    def load_group_to_default_opinion(excel_data: dict) -> dict[str, str]:
        """Load group -> default opinion mappings from the "Groupe Opinion" sheet."""
        group_opinion_df = excel_data["Groupe avis défaut"]
        group_to_default_opinion = dict(
            zip(
                group_opinion_df["Groupe"],
                group_opinion_df["Avis par défaut"],
                strict=False,
            )
        )
        return group_to_default_opinion

    @staticmethod
    def load_subsidiary_table(excel_data: dict) -> pd.DataFrame:
        """Load subsidiary table for redactional amendment attribution from the "Table subsidiaire" sheet."""
        if "Table subsidiaire" not in excel_data:
            logger.warning("Sheet 'Table subsidiaire' not found in configuration file.")
            return pd.DataFrame(columns=["Numéro article", "Affectation (nom)"])

        subsidiary_df = excel_data["Table subsidiaire"].copy()
        subsidiary_df.fillna("", inplace=True)

        logger.info(f"Loaded {len(subsidiary_df)} entries from 'Table subsidiaire'.")
        return subsidiary_df
