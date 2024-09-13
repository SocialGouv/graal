import pandas as pd

from amendements_intelligents.utils.text_utils import AttributionTextNormalizer


class AttributionDataLoader:
    @staticmethod
    def load_codes_and_articles(excel_data: dict) -> pd.DataFrame:
        """Load and normalize codes and articles from the data."""
        codes_articles_df = excel_data["Code et Article"]
        codes_articles_df.rename(
            columns={"Prénom Nom": "Affectation (nom)"}, inplace=True
        )
        codes_articles_df["Articles"] = codes_articles_df["Articles"].apply(
            lambda x: AttributionTextNormalizer.normalize_text(str(x))
        )
        codes_articles_df["Code"] = codes_articles_df["Code"].apply(
            lambda x: AttributionTextNormalizer.normalize_text(str(x))
        )
        return codes_articles_df

    @staticmethod
    def load_keywords(excel_data: dict) -> pd.DataFrame:
        """Load and normalize keywords from the data."""
        keywords_df = excel_data["Mots clés"]
        keywords_df["Mots clés"] = keywords_df["Mots clés"].apply(
            lambda x: AttributionTextNormalizer.normalize_text(str(x))
        )
        keywords_df.rename(columns={"Prénom Nom": "Affectation (nom)"}, inplace=True)
        return keywords_df

    @staticmethod
    def load_name_email_mappings(excel_data: dict) -> dict[str, str]:
        """Load name and email mappings from the "Prénom Nom Mail" sheet."""
        name_email_df = excel_data["Prénom Nom Mail"]
        name_email_mappings = dict(
            zip(name_email_df["Prénom Nom"], name_email_df["Mail"])
        )
        return name_email_mappings

    @staticmethod
    def load_attribution_mappings_when_empty(excel_data: dict) -> list[str]:
        attribution_mappings_when_empty = excel_data["Attribution par défault"][
            "Prénom Nom"
        ].tolist()
        return attribution_mappings_when_empty

    @staticmethod
    def load_group_to_default_opinion(excel_data: dict) -> dict[str, str]:
        """Load group to default opinion mappings from the "Groupe Opinion" sheet."""
        group_opinion_df = excel_data["Groupe avis défaut"]
        group_to_default_opinion = dict(
            zip(group_opinion_df["Groupe"], group_opinion_df["Avis par défaut"])
        )
        return group_to_default_opinion
