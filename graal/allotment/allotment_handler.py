import logging
import logging.config
from typing import Callable

import pandas as pd

from graal.clustering.cluster_finder import AmendmentsClusterFinder
from graal.custom_types import Acronym, IntIndex
from graal.utils.amendment_pre_processor import AmendmentPreProcessor

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
        amendments_df: pd.DataFrame, acronym_mapping: dict[Acronym, str]
    ) -> pd.DataFrame:
        prepared_df = AmendmentPreProcessor.clear_columns_to_be_overridden(
            amendments_df=amendments_df, columns_to_clear=["Allotissement"]
        )
        prepared_df = AmendmentPreProcessor.replace_acronyms(
            amendments_df=prepared_df,
            acronym_mapping=acronym_mapping,
            columns_to_normalize=["Corps amdt"],
        )
        prepared_df = AmendmentPreProcessor.drop_empty_rows_in_columns(
            amendments_df=prepared_df, columns_to_filter=["Corps amdt"]
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
        group_by_columns: list[str],
    ) -> dict[tuple, list[list[IntIndex]]]:
        # Clustering
        logging.info("Get clusters of similar amendments")
        cluster_finder = AmendmentsClusterFinder(
            amendments_df=normalized_amdt_df, group_by_columns=group_by_columns
        )
        cluster_finder.find_similarity_clusters(eps=0.0001)
        allotted_amdt_clusters = cluster_finder.refine_clusters_with_distance(
            threshold=0.0001
        )
        return allotted_amdt_clusters

    @staticmethod
    def default_removal_strategy_func(
        _df: pd.DataFrame, cluster: list[IntIndex]
    ) -> list[IntIndex]:
        return cluster[1:]

    @staticmethod
    def filter_amdts_to_keep_one_per_allotment(
        normalized_amdt_df: pd.DataFrame,
        allotted_amdt_clusters: dict[tuple, list[list[IntIndex]]],
        removal_strategy_func: Callable[
            [pd.DataFrame, list[IntIndex]], list[IntIndex]
        ] = default_removal_strategy_func,
    ) -> pd.DataFrame:
        logging.info("Keep only one amendment per allotment")
        extracted_amdt_indices = []

        for clusters in allotted_amdt_clusters.values():
            for cluster in clusters:
                amdt_indices_to_remove = removal_strategy_func(
                    normalized_amdt_df, cluster
                )
                extracted_amdt_indices.extend(amdt_indices_to_remove)

        filtered_normalized_df = normalized_amdt_df[
            ~normalized_amdt_df["amdt_idx"].isin(extracted_amdt_indices)
        ]

        return filtered_normalized_df

    @staticmethod
    def populate(
        original_amendments_df: pd.DataFrame,
        pipeline_result_amdt_df: pd.DataFrame,
        allotted_amdt_clusters: dict[tuple, list[list[IntIndex]]],
        columns_to_copy: list[str] | None,
    ) -> pd.DataFrame:
        logging.info(
            "Copying columns from the first amendment of each allotment cluster to all others"
        )

        valid_columns_to_copy = []
        if columns_to_copy:
            valid_columns_to_copy = [
                col for col in columns_to_copy if col in pipeline_result_amdt_df.columns
            ]
            mask = original_amendments_df["amdt_idx"].isin(
                pipeline_result_amdt_df["amdt_idx"]
            )
            original_amendments_df.loc[mask, valid_columns_to_copy] = (
                pipeline_result_amdt_df.loc[
                    pipeline_result_amdt_df["amdt_idx"].isin(
                        original_amendments_df["amdt_idx"]
                    ),
                    valid_columns_to_copy,
                ].values
            )

        for clusters in allotted_amdt_clusters.values():
            for cluster in clusters:
                cluster_mask = original_amendments_df["amdt_idx"].isin(cluster)
                cluster_num_amdt = original_amendments_df.loc[
                    cluster_mask, "Num amdt"
                ].sort_values()
                cluster_num_amdt_str = ",".join(map(str, cluster_num_amdt))

                original_amendments_df.loc[cluster_mask, "Allotissement"] = (
                    cluster_num_amdt_str
                )

                if valid_columns_to_copy:
                    amdt_row_with_values = original_amendments_df.loc[
                        cluster_mask
                        & original_amendments_df[valid_columns_to_copy]
                        .notnull()
                        .all(axis=1)
                    ].iloc[0]
                    original_amendments_df.loc[cluster_mask, valid_columns_to_copy] = (
                        amdt_row_with_values[valid_columns_to_copy].values
                    )

        return original_amendments_df
