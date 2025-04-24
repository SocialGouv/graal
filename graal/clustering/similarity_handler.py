import logging
import logging.config
import textwrap
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
        amendments_df = AmendmentPreProcessor.drop_empty_rows_in_columns(
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
    def filter_old_amendments_by_project(
        preprocessed_old_amendments_df: pd.DataFrame,
        preprocessed_new_amendments_df: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Filters old amendments by project based on the corresponding values in the first row of
        new amendments.
        """
        first_new_amendment = preprocessed_new_amendments_df.iloc[0]
        origin_project = first_new_amendment["origin_project"]

        return preprocessed_old_amendments_df[
            (preprocessed_old_amendments_df["origin_project"] == origin_project)
        ]

    @staticmethod
    def populate(
        preprocessed_old_amendments_df: pd.DataFrame,
        preprocessed_new_amendments_df: pd.DataFrame,
        original_new_amendments_df: pd.DataFrame,
        clustering_similarity_thresholds: dict[ColumnName, float],
        fuzzy_match_similarity_thresholds: dict[ColumnName, float],
        similarity_threshold_overrides: dict[ColumnName, dict[str, float]],
        column_group_by_columns: dict[ColumnName, list[ColumnName]],
        columns_to_copy_config: dict,
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
            # In some cases we want to look for similarity only in a subset of the old amendments (origin_project) for example
            filter_func = column_filtering_funcs.get(column, lambda x, _y: x)
            df_to_compare = filter_func(
                preprocessed_old_amendments_df, preprocessed_new_amendments_df
            )
            if df_to_compare.empty:
                logging.warning(
                    f"No old amendments to compare for column {column}. Skipping..."
                )
                continue
            similarity_finder = SimilarityFinder(
                old_amendments_df=df_to_compare,
                new_amendments_df=preprocessed_new_amendments_df,
                group_by_columns=column_group_by_columns.get(column, None),
            )
            clusters = similarity_finder.clusterize_similar_amdts(
                column_used_for_clustering=column,
                clustering_similarity_threshold=clustering_similarity_thresholds.get(
                    column, default_clustering_similarity_threshold
                ),
            )

            closest_amdts = similarity_finder.find_best_matches(
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
            columns_config=columns_to_copy_config,
        )

        return new_amendments_with_copies_df

    @staticmethod
    def copy_matches_to_amendments_df(
        target_df: pd.DataFrame,
        old_amendments_df: pd.DataFrame,
        closest_amdts: dict,
        columns_config: dict,
    ) -> pd.DataFrame:
        # Default configuration if none provided

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
                # Extract the matching details
                matching_origin_project = matching_amendment["origin_project"].values[0]
                matching_num_amdt = matching_amendment["Num amdt"].values[0]
                matching_lecture = (
                    matching_amendment["Lecture"].values[0]
                    if "Lecture" in matching_amendment.columns
                    else ""
                )
                matching_organe = (
                    matching_amendment["Organe"].values[0]
                    if "Organe" in matching_amendment.columns
                    else ""
                )

                # Update target DataFrame with the matched details
                current_comments = target_df.loc[amdt_idx_mask, "Commentaires"].values[
                    0
                ]
                if current_comments:
                    target_df.loc[amdt_idx_mask, "Commentaires"] += "\n"
                else:
                    target_df.loc[amdt_idx_mask, "Commentaires"] = ""

                target_df.loc[amdt_idx_mask, "Commentaires"] += textwrap.dedent(f"""
                        Réponse copiée de : {matching_origin_project}
                        Numéro d'amendement : {matching_num_amdt}
                        Lecture : {matching_lecture}
                        Organe : {matching_organe}
                        Colonne similaire : {column_used_for_comparison}
                    """).strip()

                # Process each configured column
                for column_name, column_config in columns_config.items():
                    # Skip disabled columns
                    if not column_config.get("enabled", False):
                        continue

                    # Check if the column exists in the matching amendment
                    if column_name in matching_amendment.columns:
                        old_value = matching_amendment[column_name].values[0]

                        # Check if there's a condition for copying
                        if "condition" in column_config and pd.notna(old_value):
                            condition = column_config["condition"]
                            if condition.lower() in str(old_value).lower():
                                target_df.loc[amdt_idx_mask, column_name] = old_value
                                # Add to comments
                                target_df.loc[amdt_idx_mask, "Commentaires"] += (
                                    f"\n{column_name} copié : {old_value}"
                                )
                        else:
                            # No condition, just copy
                            target_df.loc[amdt_idx_mask, column_name] = old_value

        return target_df
