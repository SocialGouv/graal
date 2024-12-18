import logging
import logging.config
import textwrap
from datetime import datetime
from typing import Callable, Optional

import pandas as pd

from graal.clustering.similarity_finder import SimilarityFinder
from graal.custom_types import ColumnName
from graal.utils.amendment_pre_processor import AmendmentPreProcessor

logging.config.fileConfig("logging.conf")


class SimilarityHandler:
    @staticmethod
    def preprocess_for_similarity(
        amendments_df: pd.DataFrame, acronym_mapping: dict[str, str]
    ) -> pd.DataFrame:
        amendments_df = AmendmentPreProcessor.remap_columns_in_json_amendments(
            amendments_df=amendments_df
        )
        amendments_df = AmendmentPreProcessor.replace_acronyms(
            amendments_df=amendments_df,
            acronym_mapping=acronym_mapping,
            columns_to_normalize=["Exposé amdt", "Corps amdt"],
        )
        amendments_df = AmendmentPreProcessor.remove_empty_rows_for_given_columns(
            amendments_df=amendments_df,
            columns_to_filter=["Exposé amdt", "Corps amdt", "Num article"],
        )
        amendments_df = AmendmentPreProcessor.handle_common_amendment_bodies(
            amendments_df=amendments_df
        )
        amendments_df = AmendmentPreProcessor.handle_common_amendment_expose(
            amendments_df=amendments_df
        )
        amendments_df = AmendmentPreProcessor.normalize_amendments(
            amendments_df=amendments_df,
            columns_to_normalize=["Exposé amdt", "Corps amdt"],
        )

        return amendments_df

    @staticmethod
    def filter_old_amendments_by_project_and_year(
        preprocessed_old_amendments_df: pd.DataFrame,
        preprocessed_new_amendments_df: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Filters old amendments by project and year based on the corresponding values in the first row of
        new amendments.
        """
        first_new_amendment = preprocessed_new_amendments_df.iloc[0]
        origin_project = first_new_amendment["origin_project"]
        timestamp = first_new_amendment["timestamp"]
        year = datetime.fromtimestamp(timestamp).year

        return preprocessed_old_amendments_df[
            (preprocessed_old_amendments_df["origin_project"] == origin_project)
            & (
                preprocessed_old_amendments_df["timestamp"].apply(
                    lambda x: datetime.fromtimestamp(x).year
                )
                == year
            )
        ]

    @staticmethod
    def populate(
        preprocessed_old_amendments_df: pd.DataFrame,
        preprocessed_new_amendments_df: pd.DataFrame,
        original_new_amendments_df: pd.DataFrame,
        clustering_similarity_thresholds: dict[ColumnName, float],
        fuzzy_match_similarity_thresholds: dict[ColumnName, float],
        similarity_threshold_overrides: dict[ColumnName, dict[str, float]],
        default_clustering_similarity_threshold: float = 0.4,
        default_fuzzy_match_similarity_threshold: float = 0.9,
        column_filtering_funcs: Optional[
            dict[ColumnName, Callable[[pd.DataFrame, pd.DataFrame], pd.DataFrame]]
        ] = None,
    ) -> pd.DataFrame:
        if column_filtering_funcs is None:
            column_filtering_funcs = {}
        columns_to_process = clustering_similarity_thresholds.keys()

        merged_closest_amdts: dict[int, dict] = {}

        for column in columns_to_process:
            # In some cases we don't want to look for similarity in all old amendments so we have this filter here
            filter_func = column_filtering_funcs.get(column, lambda x, _y: x)
            df_to_compare = filter_func(
                preprocessed_old_amendments_df, preprocessed_new_amendments_df
            )
            similarity_evaluator = SimilarityFinder(
                old_amendments_df=df_to_compare,
                new_amendments_df=preprocessed_new_amendments_df,
            )
            clusters = similarity_evaluator.clusterize_similar_amdts(
                column_used_for_clustering=column,
                clustering_similarity_threshold=clustering_similarity_thresholds.get(
                    column, default_clustering_similarity_threshold
                ),
            )

            closest_amdts = similarity_evaluator.find_best_matches(
                column_used_for_similarity=column,
                clusters=clusters,
                fuzzy_match_similarity_threshold=fuzzy_match_similarity_thresholds.get(
                    column, default_fuzzy_match_similarity_threshold
                ),
                similarity_threshold_overrides=similarity_threshold_overrides.get(
                    column, {}
                ),
            )

            for amdt_idx, match in closest_amdts.items():
                if amdt_idx in merged_closest_amdts:
                    existing_match = merged_closest_amdts[amdt_idx]
                    if match["similarity_ratio"] > existing_match["similarity_ratio"]:
                        merged_closest_amdts[amdt_idx] = match
                else:
                    merged_closest_amdts[amdt_idx] = match

        # Copy matched amendments to new_amendments_df
        new_amendments_with_copies_df = SimilarityHandler.copy_matches_to_amendments_df(
            target_df=original_new_amendments_df,
            old_amendments_df=preprocessed_old_amendments_df,
            closest_amdts=merged_closest_amdts,
        )

        return new_amendments_with_copies_df

    @staticmethod
    def copy_matches_to_amendments_df(
        target_df: pd.DataFrame, old_amendments_df: pd.DataFrame, closest_amdts: dict
    ) -> pd.DataFrame:
        # Iterate over the closest documents
        for new_amdt_idx, closest_doc in closest_amdts.items():
            amdt_idx_mask = target_df["amdt_idx"] == new_amdt_idx

            # Get the best match details
            best_matching_doc_amdt_idx = closest_doc["best_matching_doc_amdt_idx"]
            column_used_for_comparison = closest_doc["column_used_for_comparison"]

            # Filter old amendments for the best match
            old_amendment_mask = (
                old_amendments_df["amdt_idx"] == best_matching_doc_amdt_idx
            )
            matching_amendment = old_amendments_df.loc[old_amendment_mask]

            if not matching_amendment.empty:
                # Copy the response if available
                target_df.loc[amdt_idx_mask.values, "Réponse"] = matching_amendment[
                    "Réponse"
                ].values[0]

                # Extract the matching details
                matching_origin_project = matching_amendment["origin_project"].values[0]
                matching_num_amdt = matching_amendment["Num amdt"].values[0]
                matching_lecture = matching_amendment["Lecture"].values[0]
                matching_organe = matching_amendment["Organe"].values[0]
                matching_timestamp = -closest_doc["best_matching_comparison_value"]
                matching_year = datetime.fromtimestamp(matching_timestamp).year

                # Update target DataFrame with the matched details
                current_comments = target_df.loc[amdt_idx_mask, "Commentaires"].values[
                    0
                ]
                if current_comments:
                    target_df.loc[amdt_idx_mask, "Commentaires"] += "\n"
                else:
                    target_df.loc[amdt_idx_mask, "Commentaires"] = ""

                target_df.loc[amdt_idx_mask, "Commentaires"] += textwrap.dedent(f"""
                        Réponse copiée de : {matching_origin_project} {matching_year}
                        Numéro d'amendement : {matching_num_amdt}
                        Lecture : {matching_lecture}
                        Organe : {matching_organe}
                        Colonne similaire : {column_used_for_comparison}
                    """).strip()

                # Check and copy the "Sort" value if it contains "Irrecevable"
                old_sort_value = matching_amendment["Sort"].values[0]
                if pd.notna(old_sort_value) and "irrecevable" in old_sort_value.lower():
                    target_df.loc[amdt_idx_mask, "Sort"] = old_sort_value
                    target_df.loc[amdt_idx_mask, "Commentaires"] += "\n"
                    target_df.loc[amdt_idx_mask, "Commentaires"] += textwrap.dedent(f"""
                            Sort copié : {old_sort_value}
                        """).strip()

        return target_df
