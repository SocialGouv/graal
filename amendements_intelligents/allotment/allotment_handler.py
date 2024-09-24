import logging
import logging.config

import pandas as pd

from amendements_intelligents.clustering.cluster_finder import AmendmentsClusterFinder
from amendements_intelligents.types import IntIndex
from amendements_intelligents.utils.amendment_pre_processor import AmendmentPreProcessor

logging.config.fileConfig("logging.conf")


class AllotmentHandler:
    @staticmethod
    def preprocess_json_amendments(
        amendments_df: pd.DataFrame,
    ) -> pd.DataFrame:
        amendments_df = AmendmentPreProcessor.remap_columns_in_json_amendments(
            amendments_df=amendments_df
        )

        return amendments_df

    @staticmethod
    def preprocess_amendments(
        amendments_df: pd.DataFrame, acronym_mapping: dict[str, str]
    ) -> pd.DataFrame:
        prepared_df = AmendmentPreProcessor.clear_columns_to_be_overridden(
            amendments_df=amendments_df, columns_to_clear=["Allotissement"]
        )
        prepared_df = AmendmentPreProcessor.replace_acronyms(
            amendments_df=prepared_df,
            acronym_mapping=acronym_mapping,
            columns_to_normalize=["Corps amdt"],
        )
        prepared_df = AmendmentPreProcessor.remove_empty_rows_for_given_columns(
            amendments_df=prepared_df, columns_to_filter_with=["Corps amdt"]
        )
        prepared_df = AmendmentPreProcessor.handle_common_amendment_bodies(
            amendments_df=prepared_df
        )
        prepared_df = AmendmentPreProcessor.normalize_amendments(
            amendments_df=prepared_df, columns_to_normalize=["Corps amdt"]
        )

        return prepared_df

    @staticmethod
    def get_clusters(
        normalized_amdt_df: pd.DataFrame,
    ) -> dict[str, list[list[IntIndex]]]:
        # Clustering
        cluster_finder = AmendmentsClusterFinder(amendments_df=normalized_amdt_df)
        cluster_finder.find_similarity_clusters(eps=0.0001)
        aloted_amdt_clusters = cluster_finder.refine_clusters_with_distance(
            threshold=0.0001
        )
        return aloted_amdt_clusters

    @staticmethod
    def filter_amdts_to_keep_one_per_allotment(
        normalized_amdt_df: pd.DataFrame,
        aloted_amdt_clusters: dict[str, list[list[IntIndex]]],
    ) -> pd.DataFrame:
        extracted_amdt_indices = []

        for clusters in aloted_amdt_clusters.values():
            for cluster in clusters:
                extracted_amdt_indices.extend(cluster[1:])  # Extract the rest

        filtered_normalized_df = normalized_amdt_df[
            ~normalized_amdt_df["amdt_idx"].isin(extracted_amdt_indices)
        ]

        return filtered_normalized_df

    @staticmethod
    def populate(
        original_amendments_df: pd.DataFrame,
        pipeline_result_amdt_df: pd.DataFrame,
        aloted_amdt_clusters: dict[str, list[list[int]]],
        columns_to_copy: list[str],
    ) -> pd.DataFrame:
        # Iterate over the clusters only once
        for _lecture, clusters in aloted_amdt_clusters.items():
            for cluster in clusters:
                # Get the first amendment in the cluster
                first_amdt_idx = cluster[0]
                first_amdt_row = pipeline_result_amdt_df[
                    pipeline_result_amdt_df["amdt_idx"] == first_amdt_idx
                ].iloc[0]

                # Get the Num amdt for all amendments in the cluster and create a string for "Allotissement"
                cluster_num_amdt = sorted(
                    original_amendments_df[
                        original_amendments_df["amdt_idx"].isin(cluster)
                    ]["Num amdt"]
                )
                cluster_num_amdt_str = ",".join(map(str, cluster_num_amdt))

                # Update the original_amendments_df with the Allotissement string
                original_amendments_df.loc[
                    original_amendments_df["amdt_idx"].isin(cluster), "Allotissement"
                ] = cluster_num_amdt_str

                if columns_to_copy is None:
                    continue

                # Copy in original_amendments_df the columns_to_copy from `pipeline_result_amdt_df`.
                # The values are taken from the first amendment in the cluster (the other ones are empty)
                for amdt_idx in cluster:
                    existing_columns = [
                        col
                        for col in columns_to_copy
                        if col in pipeline_result_amdt_df.columns
                    ]

                    if existing_columns:
                        # Safely copy the columns from first_amdt_row
                        original_amendments_df.loc[
                            original_amendments_df["amdt_idx"] == amdt_idx,
                            existing_columns,
                        ] = first_amdt_row[existing_columns].values

        return original_amendments_df
