import pandas as pd


class OpinionHandler:
    def __init__(
        self,
        amendments_df: pd.DataFrame,
        group_to_default_opinion: dict[str, str],
    ):
        self.amendments_df = amendments_df
        self.group_to_default_opinion = group_to_default_opinion

    def populate(self):
        self.amendments_df["Avis du Gouvernement"] = self.amendments_df["Groupe"].map(
            self.group_to_default_opinion
        )

        return self.amendments_df
        return self.amendments_df
