import pandas as pd

from amendements_intelligents.utils.plfss_text_utils import AttributionTextNormalizer


class AttributionDataLoader:
    def __init__(self):
        self.codes_articles_df: pd.DataFrame = pd.DataFrame()
        self.keywords_df: pd.DataFrame = pd.DataFrame()

    def load_mappings(self, mappings_excel_file: str):
        """Load mappings data from an Excel file."""
        excel_data = pd.read_excel(mappings_excel_file, sheet_name=None)
        self._load_codes_and_articles(excel_data)
        self._load_keywords(excel_data)

    def _load_codes_and_articles(self, excel_data: dict):
        """Load and normalize codes and articles from the data."""
        self.codes_articles_df = excel_data["Code et Article"]
        self.codes_articles_df.rename(
            columns={"Prénom Nom": "Affectation (nom)"}, inplace=True
        )
        self.codes_articles_df["Articles"] = self.codes_articles_df["Articles"].apply(
            lambda x: AttributionTextNormalizer.normalize_text(str(x))
        )
        self.codes_articles_df["Code"] = self.codes_articles_df["Code"].apply(
            lambda x: AttributionTextNormalizer.normalize_text(str(x))
        )

    def _load_keywords(self, excel_data: dict):
        """Load and normalize keywords from the data."""
        self.keywords_df = excel_data["Mots clés"]
        self.keywords_df["Mots clés"] = self.keywords_df["Mots clés"].apply(
            lambda x: AttributionTextNormalizer.normalize_text(str(x))
        )
        self.keywords_df.rename(
            columns={"Prénom Nom": "Affectation (nom)"}, inplace=True
        )
