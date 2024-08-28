import os
import time

import pandas as pd
from pydantic import FilePath

from amendements_intelligents.clustering.cluster_finder import PLFSSClusterFinder
from amendements_intelligents.utils.plfss_allotment_updater import PLFSSAllotmentUpdater
from amendements_intelligents.utils.plfss_pre_processor import PLFSSPreProcessor


class PLFSSAllotmentPopulator:
    def __init__(self) -> None:
        self.amendements_df = None
        self.prepared_df = None

    def load_data(self, input_file: FilePath, year: int = None) -> None:
        self.amendements_df = PLFSSPreProcessor.load_plfss_json(
            input_files=[(input_file, year)]
        )

    def preprocess(self, acronym_file: FilePath) -> None:
        plfss_pre_processor = PLFSSPreProcessor
        acronym_mapping = plfss_pre_processor.load_acronyms_excel(acronym_file)
        self.amendements_df = plfss_pre_processor.remap_columns_in_json_amendments(
            amendments_df=self.amendements_df
        )
        self.prepared_df = plfss_pre_processor.prepare_amendments_columns(
            amendments_df=self.amendements_df
        )
        self.prepared_df = plfss_pre_processor.replace_acronyms(
            amendments_df=self.prepared_df,
            acronym_mapping=acronym_mapping,
            columns_to_normalize=["Corps amdt"],
        )
        self.prepared_df = plfss_pre_processor.remove_empty_rows_for_given_columns(
            amendments_df=self.prepared_df, columns_to_filter_with=["Corps amdt"]
        )
        self.prepared_df = plfss_pre_processor.handle_common_amendment_bodies(
            amendments_df=self.prepared_df
        )
        self.prepared_df = plfss_pre_processor.normalize_plfss(
            amendments_df=self.prepared_df, columns_to_normalize=["Corps amdt"]
        )

    def process(self) -> pd.DataFrame:
        # Clustering
        cluster_finder = PLFSSClusterFinder(amendments_df=self.amendements_df)
        final_clusters = cluster_finder.find_similarity_clusters(eps=0.01)
        final_clusters = cluster_finder.refine_clusters_with_exact_match(
            threshold=0.0001
        )

        # Result processing
        allotment_updater = PLFSSAllotmentUpdater(
            original_amendments_df=self.amendements_df,
            work_amendments_df=self.prepared_df,
            final_clusters=final_clusters,
        )
        return allotment_updater.update_allotissement()


def main():
    start_time = time.time()
    DATA_FOLDER = os.getenv("DATA_FOLDER", "data")
    INPUT_FILE = f"{DATA_FOLDER}/PLFSS 2024.json"
    OUTPUT_FILE = f"{DATA_FOLDER}/amendments_with_allotments.xlsx"
    COLUMNS_TO_OUTPUT = [
        "Lecture",
        "Num amdt",
        "Num article",
        "Allotissement",
        "Corps amdt",
        "Exposé amdt",
    ]

    allotment_populator = PLFSSAllotmentPopulator()
    allotment_populator.load_data(input_file=INPUT_FILE)
    allotment_populator.preprocess(acronym_file=f"{DATA_FOLDER}/acronym_mapping.xlsx")
    amendments_df = allotment_populator.process()

    amendments_df[COLUMNS_TO_OUTPUT].to_excel(OUTPUT_FILE, index=False)
    print(f"Saved result in {OUTPUT_FILE}\n")

    end_time = time.time()
    execution_time = end_time - start_time
    print("Script execution time:", execution_time, "seconds")


if __name__ == "__main__":
    main()
