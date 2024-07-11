import re

import pandas as pd


class PLFSSTextProcessor:
    MIN_LENGTH_EXPOSE_TO_PROCESS = 50

    @staticmethod
    def normalize_text(text: str):
        text = text.strip()
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
    def preprocess_df(plfss_df: pd.DataFrame):
        result_df = plfss_df.dropna(subset=["Exposé des motifs"]).copy()
        result_df = result_df[
            result_df["Exposé des motifs"] != "Amendement rédactionnel."
        ]
        result_df = result_df[
            result_df["Exposé des motifs"].str.len()
            >= PLFSSTextProcessor.MIN_LENGTH_EXPOSE_TO_PROCESS
        ]
        result_df["Exposé des motifs"] = result_df["Exposé des motifs"].apply(
            PLFSSTextProcessor.normalize_text
        )
        return result_df
