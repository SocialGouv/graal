import pandas as pd

from amendements_intelligents.types import IntIndex


class AllotmentUpdater:
    def __init__(
        self,
        original_amendments_df: pd.DataFrame,
        normalized_amendments_df: pd.DataFrame,
        final_clusters: dict[str, list[list[IntIndex]]],
    ) -> None:
        self.amendments_df = original_amendments_df
        self.normalized_amendements_df = normalized_amendments_df
        self.final_clusters = final_clusters

    def update_allotissement(self) -> pd.DataFrame:
        for lecture, clusters in self.final_clusters.items():
            df_group = self.normalized_amendements_df[
                self.normalized_amendements_df["Lecture"] == lecture
            ]
            for cluster_indices in clusters:
                # Get the Num amdt for the indices in cluster_indices based on amdt_idx
                cluster_num_amdt = sorted(
                    df_group[df_group["amdt_idx"].isin(cluster_indices)]["Num amdt"]
                )
                cluster_num_amdt_str = ",".join(map(str, cluster_num_amdt))

                for amdt_idx in cluster_indices:
                    # Get the Num amdt for the current amdt_idx
                    num_amdt = df_group[df_group["amdt_idx"] == amdt_idx][
                        "Num amdt"
                    ].values[0]
                    mask = (self.amendments_df["Num amdt"] == num_amdt) & (
                        self.amendments_df["Lecture"] == lecture
                    )
                    self.amendments_df.loc[mask, "Allotissement"] = cluster_num_amdt_str

        return self.amendments_df
