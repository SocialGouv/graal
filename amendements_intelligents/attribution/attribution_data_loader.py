import pandas as pd

from amendements_intelligents.utils.plfss_text_utils import AttributionTextNormalizer


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
