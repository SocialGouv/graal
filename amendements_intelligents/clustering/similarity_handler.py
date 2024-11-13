import logging
import logging.config

import pandas as pd

from amendements_intelligents.clustering.similarity_finder import SimilarityFinder
from amendements_intelligents.types import ColumnName
from amendements_intelligents.utils.amendment_copier import AmendmentCopier
from amendements_intelligents.utils.amendment_pre_processor import AmendmentPreProcessor

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
            columns_to_filter_with=["Exposé amdt", "Corps amdt"],
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
    def populate(
        preprocessed_old_amendments_df: pd.DataFrame,
        preprocessed_new_amendments_df: pd.DataFrame,
        original_new_amendments_df: pd.DataFrame,
        clustering_similarity_thresholds: dict[ColumnName, float],
        fuzzy_match_similarity_thresholds: dict[ColumnName, float],
        similarity_threshold_overrides: dict[ColumnName, dict[str, float]],
        default_clustering_similarity_threshold: float = 0.4,
        default_fuzzy_match_similarity_threshold: float = 0.9,
    ) -> pd.DataFrame:
        similarity_evaluator_expose = SimilarityFinder(
            old_amendments_df=preprocessed_old_amendments_df,
            new_amendments_df=preprocessed_new_amendments_df,
        )

        columns_to_process = clustering_similarity_thresholds.keys()

        merged_closest_amdts: dict = {}

        for column in columns_to_process:
            clusters = similarity_evaluator_expose.clusterize_similar_amdts(
                column_used_for_clustering=column,
                clustering_similarity_threshold=clustering_similarity_thresholds.get(
                    column, default_clustering_similarity_threshold
                ),
            )

            closest_amdts = similarity_evaluator_expose.find_best_matches(
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
        amendment_copier = AmendmentCopier(
            new_amendments_df=preprocessed_new_amendments_df,
            old_amendments_df=preprocessed_old_amendments_df,
            closest_amdts=merged_closest_amdts,
        )
        new_amendments_with_copies_df = amendment_copier.copy_matches_to_amendments_df(
            target_df=original_new_amendments_df
        )

        return new_amendments_with_copies_df
