import pandas as pd


class PLFSSDataLoader:
    def __init__(self, df: pd.DataFrame):
        self.df = df

    def filter_amendements(self):
        # Filter rows where 'Exposé des motifs' is not empty
        filtered_df = self.df[self.df["Exposé des motifs"].notnull()]

        mean_length = filtered_df["Exposé des motifs"].str.len().mean()
        length_around_mean_to_keep = 500

        # Filter rows where the length of 'Exposé des motifs' is between mean ± length_around_mean_to_keep
        result_df = filtered_df[
            (
                filtered_df["Exposé des motifs"].str.len()
                >= mean_length - length_around_mean_to_keep
            )
            & (
                filtered_df["Exposé des motifs"].str.len()
                <= mean_length + length_around_mean_to_keep
            )
        ]

        return result_df[
            [
                "Exposé des motifs",
                "Numéro",
                "Objet",
                "Commentaires",
                "Chargé de mission",
            ]
        ]
