import pandas as pd

from amendements_intelligents.utils.text_utils import AttributionTextNormalizer


class AttributionDataLoader:
    @staticmethod
    def load_codes_and_articles(excel_data: dict) -> pd.DataFrame:
        """Load and normalize codes and articles from the data."""
        codes_articles_df = excel_data["Code et Article"].copy()
        codes_articles_df["Type"] = codes_articles_df["Type"].str.lower()
        codes_articles_df = codes_articles_df[
            codes_articles_df["Type"].str.contains("code", na=False)
        ]
        codes_articles_df.loc[:, "Articles"] = codes_articles_df["Articles"].apply(
            lambda x: AttributionTextNormalizer.normalize_text(str(x))
        )
        codes_articles_df.loc[:, "Valeur"] = codes_articles_df["Valeur"].apply(
            lambda x: AttributionTextNormalizer.normalize_text(str(x))
        )
        codes_articles_df.rename(
            columns={"Prénom Nom": "Affectation (nom)", "Valeur": "value"}, inplace=True
        )
        return codes_articles_df

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
    def load_name_email_mappings(excel_data: dict) -> dict[str, str]:
        """Load name and email mappings from the "Prénom Nom Mail" sheet."""
        name_email_df = excel_data["Prénom Nom Mail"]
        name_email_mappings = dict(
            zip(name_email_df["Prénom Nom"], name_email_df["Mail"])
        )
        return name_email_mappings

    @staticmethod
    def load_default_attribution_mappings(excel_data: dict) -> list[str]:
        """Load default attribution mappings from the "Attribution par défault" sheet. Used when no other attribution is found."""
        attribution_mappings_when_empty = excel_data["Attribution par défault"][
            "Prénom Nom"
        ].tolist()
        return attribution_mappings_when_empty

    @staticmethod
    def load_group_to_default_opinion(excel_data: dict) -> dict[str, str]:
        """Load group -> default opinion mappings from the "Groupe Opinion" sheet."""
        group_opinion_df = excel_data["Groupe avis défaut"]
        group_to_default_opinion = dict(
            zip(group_opinion_df["Groupe"], group_opinion_df["Avis par défaut"])
        )
        return group_to_default_opinion
