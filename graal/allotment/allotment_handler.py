import logging
import logging.config
from typing import Callable, Dict, List, Optional, Tuple

import pandas as pd

from graal.clustering.clustering_service import ClusteringService
from graal.custom_types import Acronym, IntIndex
from graal.utils.amendment_pre_processor import AmendmentPreProcessor

logging.config.fileConfig("logging.conf")


class AllotmentHandler:
    """Handler for grouping amendments into allotments."""

    @staticmethod
    def preprocess_json_amendments(
        amendments_df: pd.DataFrame,
    ) -> pd.DataFrame:
        amendments_df = AmendmentPreProcessor.remap_columns_in_json_amendments(
            amendments_df=amendments_df
        )

        return amendments_df

    @staticmethod
    def preprocess_amendments_for_allotment(
        amendments_df: pd.DataFrame,
        acronym_mapping: Dict[Acronym, str],
        column: str = "Corps amdt",
    ) -> pd.DataFrame:
        """Specialized preprocessing for allotment."""
        prepared_df = AmendmentPreProcessor.clear_columns_to_be_overridden(
            amendments_df=amendments_df, columns_to_clear=["Allotissement"]
        )

        return ClusteringService.preprocess_amendments(
            amendments_df=prepared_df,
            columns_to_filter=[column],
            columns_to_normalize=[column],
            acronym_mapping=acronym_mapping,
        )

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
                    amdt_row_with_values = (
                        original_amendments_df.loc[cluster_mask, valid_columns_to_copy]
                        .notnull()
                        .sum(axis=1)
                        .idxmax()
                    )
                    amdt_row_with_values = original_amendments_df.loc[
                        amdt_row_with_values
                    ]
                    original_amendments_df.loc[cluster_mask, valid_columns_to_copy] = (
                        amdt_row_with_values[valid_columns_to_copy].values
                    )

        return original_amendments_df

    @staticmethod
    def process_allotments(
        amendments_df: pd.DataFrame,
        allotment_column: str,
        similarity_threshold: float = 0.0001,
        group_by_columns: Optional[List[str]] = None,
        eps: float = 0.4,
        acronym_mapping: Optional[Dict[Acronym, str]] = None,
        removal_strategy_func: Optional[Callable] = None,
    ) -> Tuple[pd.DataFrame, Dict[Tuple, List[List[IntIndex]]]]:
        """
        Process allotments in a single method that orchestrates the entire workflow

        Args:
            amendments_df: The dataframe containing amendments
            allotment_column: The column to use for allotment
            similarity_threshold: Threshold for Levenshtein refinement
            group_by_columns: Columns to group by
            eps: Epsilon value for DBSCAN
            acronym_mapping: Optional mapping of acronyms to full text
            removal_strategy_func: Strategy for removing amendments from clusters

        Returns:
            Tuple containing:
            - The filtered dataframe with one amendment per allotment
            - The clusters of allotted amendments
        """
        # Preprocess amendments
        if group_by_columns is None:
            group_by_columns = ["Num article"]
        normalized_df = ClusteringService.preprocess_amendments(
            amendments_df=amendments_df,
            columns_to_filter=[allotment_column],
            columns_to_normalize=[allotment_column],
            acronym_mapping=acronym_mapping,
            columns_to_clear=["Allotissement"],
        )

        # Get clusters
        allotted_amdt_clusters = ClusteringService.get_clusters(
            normalized_amdt_df=normalized_df,
            group_by_columns=group_by_columns,
            eps=eps,
            threshold=similarity_threshold,
            is_similarity_threshold=False,
        )

        # Filter amendments
        if removal_strategy_func is None:
            removal_strategy_func = AllotmentHandler.default_removal_strategy_func

        filtered_df = AllotmentHandler.filter_amdts_to_keep_one_per_allotment(
            normalized_amdt_df=normalized_df,
            allotted_amdt_clusters=allotted_amdt_clusters,
            removal_strategy_func=removal_strategy_func,
        )

        return filtered_df, allotted_amdt_clusters
