import os
import time
from typing import Tuple

import pandas as pd
from pydantic import FilePath

from amendements_intelligents.clustering.cluster_finder import PLFSSClusterFinder
from amendements_intelligents.utils.plfss_allotment_updater import PLFSSAllotmentUpdater
from amendements_intelligents.utils.plfss_pre_processor import PLFSSPreProcessor


class PLFSSAllotmentPopulator:
    @staticmethod
    def preprocess(
        amendments_df: pd.DataFrame, acronym_file: FilePath
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Returns a tuple of the original amendments dataframe with a small cleanup and the dataframe prepared for processing"""
        plfss_pre_processor = PLFSSPreProcessor

        acronym_mapping = plfss_pre_processor.load_acronyms_excel(acronym_file)

        amendments_df = plfss_pre_processor.remap_columns_in_json_amendments(
            amendments_df=amendments_df
        )
        # split
        prepared_df = plfss_pre_processor.prepare_amendments_columns(
            amendments_df=amendments_df
        )
        prepared_df = plfss_pre_processor.replace_acronyms(
            amendments_df=prepared_df,
            acronym_mapping=acronym_mapping,
            columns_to_normalize=["Corps amdt"],
        )
        prepared_df = plfss_pre_processor.remove_empty_rows_for_given_columns(
            amendments_df=prepared_df, columns_to_filter_with=["Corps amdt"]
        )
        prepared_df = plfss_pre_processor.handle_common_amendment_bodies(
            amendments_df=prepared_df
        )
        prepared_df = plfss_pre_processor.normalize_plfss(
            amendments_df=prepared_df, columns_to_normalize=["Corps amdt"]
        )

        return amendments_df, prepared_df

    @staticmethod
    def populate(
        original_amendments_df: pd.DataFrame, prepared_df: pd.DataFrame
    ) -> pd.DataFrame:
        # Clustering
        cluster_finder = PLFSSClusterFinder(amendments_df=prepared_df)
        cluster_finder.find_similarity_clusters(eps=0.0001)
        final_clusters = cluster_finder.refine_clusters_with_distance(threshold=0.0001)

        # Result processing
        allotment_updater = PLFSSAllotmentUpdater(
            original_amendments_df=original_amendments_df,
            work_amendments_df=prepared_df,
            final_clusters=final_clusters,
        )
        populated_df = allotment_updater.update_allotissement()
        return populated_df


def main():
    start_time = time.time()
    DATA_FOLDER = os.getenv("DATA_FOLDER", "data")
    INPUT_FILE = f"{DATA_FOLDER}/PLFSS_2024.json"
    YEAR = 2024
    OUTPUT_FILE = f"{DATA_FOLDER}/amendments_with_allotments_refactor.xlsx"
    COLUMNS_TO_OUTPUT = [
        "Lecture",
        "Num amdt",
        "Num article",
        "amdt_idx",
        "Allotissement",
        "Corps amdt",
        "Exposé amdt",
    ]

    amendments_df = PLFSSPreProcessor.load_plfss_json(input_files=[(INPUT_FILE, YEAR)])
    original_amendments_df, prepared_df = PLFSSAllotmentPopulator.preprocess(
        amendments_df=amendments_df,
        acronym_file=f"{DATA_FOLDER}/acronym_mapping.xlsx",
    )
    populated_df = PLFSSAllotmentPopulator.populate(
        original_amendments_df=original_amendments_df, prepared_df=prepared_df
    )

    populated_df[COLUMNS_TO_OUTPUT].to_excel(OUTPUT_FILE, index=False)
    print(f"Saved result in {OUTPUT_FILE}\n")

    end_time = time.time()
    execution_time = end_time - start_time
    print("Script execution time:", execution_time, "seconds")


if __name__ == "__main__":
    main()
