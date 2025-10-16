import pandas as pd


class OpinionHandler:
    def __init__(
        self,
        amendments_df: pd.DataFrame,
        group_to_default_opinion: dict[str, str],
        should_overwrite: bool = True,
    ):
        self.amendments_df = amendments_df
        self.group_to_default_opinion = group_to_default_opinion
        self.should_overwrite = should_overwrite

    def populate(self):
        if self.should_overwrite:
            # Overwrite all values
            self.amendments_df["Avis du Gouvernement"] = self.amendments_df[
                "Groupe"
            ].map(self.group_to_default_opinion)
        else:
            # Only populate empty/null values
            mask = self.amendments_df["Avis du Gouvernement"].isna()
            self.amendments_df.loc[mask, "Avis du Gouvernement"] = (
                self.amendments_df.loc[
                    mask, "Groupe"
                ].map(self.group_to_default_opinion)
            )

        return self.amendments_df
