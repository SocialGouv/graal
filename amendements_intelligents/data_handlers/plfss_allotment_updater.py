import pandas as pd

from amendements_intelligents.types import IntIndex


class PLFSSAllotmentUpdater:
    def __init__(
        self,
        amendments_df: pd.DataFrame,
        preprocessed_amendments_df: pd.DataFrame,
        final_clusters: dict[str, list[list[IntIndex]]],
    ) -> None:
        self.amendments_df = amendments_df
        self.preprocessed_amendments_df = preprocessed_amendments_df
        self.final_clusters = final_clusters

    def update_allotissement(self) -> None:
        for lecture, clusters in self.final_clusters.items():
            df_group = self.preprocessed_amendments_df[
                self.preprocessed_amendments_df["Lecture"] == lecture
            ]
            for cluster_indices in clusters:
                cluster_numeros = sorted(
                    df_group.iloc[idx]["Num amdt"] for idx in cluster_indices
                )
                cluster_numeros_str = ",".join(map(str, cluster_numeros))
                for idx in cluster_indices:
                    amendment_numero = df_group.iloc[idx]["Num amdt"]
                    mask = (self.amendments_df["Num amdt"] == amendment_numero) & (
                        self.amendments_df["Lecture"] == lecture
                    )
                    self.amendments_df.loc[mask, "Allotissement"] = cluster_numeros_str
        return self.amendments_df
