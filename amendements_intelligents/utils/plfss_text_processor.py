import re

import pandas as pd


class PLFSSTextProcessor:
    @staticmethod
    def normalize_text(text: str) -> str:
        """
        Normalize the given text by removing accents, apostrophes, dashes, backticks,
        special characters, and extra whitespaces.
        """
        text = text.strip().lower()
        # Remove accents
        text = text.encode("ascii", "ignore").decode("utf-8")
        # Remove apostrophes dashes and backticks
        text = re.sub(r"['`\-_]", " ", text)
        # Remove special characters
        text = re.sub(r"[^a-zA-Z0-9\s]", "", text)
        # Remove extra whitespaces
        text = re.sub(r"\s+", " ", text)
        return text

    @staticmethod
    def preprocess_df(
        plfss_df: pd.DataFrame, min_expose_length: int = 50
    ) -> pd.DataFrame:
        """
        Preprocesses the given DataFrame by dropping rows with missing or short "Exposé des motifs" and normalizing the text.

        Args:
            plfss_df (pd.DataFrame): The PLFSS DataFrame to be preprocessed.
            min_expose_length (int, optional): The minimum length of "Exposé des motifs" to keep. Defaults to 50.
        """
        result_df = plfss_df.dropna(subset=["Exposé des motifs"]).copy()
        result_df = result_df[
            result_df["Exposé des motifs"] != "Amendement rédactionnel."
        ]
        result_df = result_df[
            result_df["Exposé des motifs"].str.len() >= min_expose_length
        ]
        result_df["Exposé des motifs"] = result_df["Exposé des motifs"].apply(
            PLFSSTextProcessor.normalize_text
        )
        return result_df
