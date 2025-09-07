import logging
import logging.config

import pandas as pd

from graal.core.text_normalizers import TextNormalizerFactory
from graal.custom_types import LegalDocumentType, PLFProgramName, UserName

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
        attribution_normalizer = TextNormalizerFactory.get_normalizer("attribution")
        articles_df = excel_data["Code et Article"].copy()
        articles_df["Type"] = articles_df["Type"].str.lower()
        articles_df = articles_df[
            articles_df["Type"].str.contains(article_type, na=False)
        ]
        articles_df.loc[:, "Articles"] = articles_df["Articles"].apply(
            lambda x: attribution_normalizer.normalize_for_feature(str(x))
        )
        articles_df.loc[:, "Valeur"] = articles_df["Valeur"].apply(
            lambda x: attribution_normalizer.normalize_for_feature(str(x))
        )
        articles_df.rename(
            columns={"Prénom Nom": "Affectation (nom)", "Valeur": "value"}, inplace=True
        )
        articles_df["Affectation (nom)"] = articles_df["Affectation (nom)"].str.lower()

        return articles_df

    @staticmethod
    def load_programs(config_excel: dict) -> dict[PLFProgramName, set[UserName]]:
        from collections import defaultdict

        attribution_normalizer = TextNormalizerFactory.get_normalizer("attribution")
        program_to_attribution: dict[PLFProgramName, set[UserName]] = defaultdict(set)
        # Load program mappings from config if available
        if "Responsables de programme" in config_excel:
            programs_df = config_excel["Responsables de programme"]
            for _, row in programs_df.iterrows():
                if pd.isna(row["Prénom Nom"]):
                    continue
                row["Prénom Nom"] = row["Prénom Nom"].lower()
                if pd.notna(row["Programme budgétaire"]):
                    program = attribution_normalizer.normalize_for_feature(
                        row["Programme budgétaire"]
                    )
                    program_to_attribution[program].add(row["Prénom Nom"])
                # "N° programme" is an alternative for credit table matching that sometimes uses the
                # program numbers instead of their names
                if pd.notna(row["N° programme"]):
                    program = attribution_normalizer.normalize_for_feature(
                        str(int(row["N° programme"]))
                    )
                    program_to_attribution[program].add(row["Prénom Nom"])
        return program_to_attribution

    @staticmethod
    def load_keywords(
        excel_data: dict, acronym_mapping: dict[str, str]
    ) -> pd.DataFrame:
        """Load and normalize keywords from the data."""
        attribution_normalizer = TextNormalizerFactory.get_normalizer("attribution")
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
            lambda x: attribution_normalizer.normalize_for_feature(str(x))
        )

        # Rename column
        keywords_df.rename(columns={"Prénom Nom": "Affectation (nom)"}, inplace=True)
        keywords_df["Affectation (nom)"] = keywords_df["Affectation (nom)"].str.lower()

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
        user_info_df["Prénom Nom"] = user_info_df["Prénom Nom"].str.lower()

        user_info_mappings = user_info_df.set_index("Prénom Nom")[
            ["Mail", "Entité Pilote"]
        ].to_dict(orient="index")
        return user_info_mappings

    @staticmethod
    def load_default_attribution_mappings(excel_data: dict) -> list[str]:
        """Load default attribution mappings from the "Attribution par défaut" sheet. Used when no other attribution is found."""
        attribution_mappings_when_empty = (
            excel_data["Attribution par défaut"]["Prénom Nom"].str.lower().tolist()
        )

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
        # Prepend "article " to non-empty "Numéro article" rows
        subsidiary_df["Numéro article"] = subsidiary_df["Numéro article"].apply(
            lambda x: f"article {str(x).lower()}"
            if str(x).strip() != "" and not str(x).lower().startswith("article ")
            else str(x).lower()
        )
        subsidiary_df.fillna("", inplace=True)

        logger.info(f"Loaded {len(subsidiary_df)} entries from 'Table subsidiaire'.")
        return subsidiary_df
