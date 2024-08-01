import os
import time

import pandas as pd
from pydantic import FilePath

from amendements_intelligents.clustering.plfss_cluster_finder import PLFSSClusterFinder
from amendements_intelligents.data_handlers.plfss_allotment_updater import (
    PLFSSAllotmentUpdater,
)
from amendements_intelligents.data_handlers.plfss_pre_processor import (
    PLFSSPreProcessor,
)


class PLFSSAllotmentPopulator:
    def __init__(self) -> None:
        self.plfss_pre_processor = PLFSSPreProcessor()

    def load_data(self, input_file: FilePath) -> None:
        self.plfss_pre_processor.load_plfss(input_file=input_file)

    def preprocess(self) -> None:
        self.plfss_pre_processor.clean_up_original_amendments()
        self.plfss_pre_processor.prepare_work_amendments_df()
        self.plfss_pre_processor.remove_empty_rows_for_given_columns()
        self.plfss_pre_processor.handle_common_amendment_bodies()
        self.plfss_pre_processor.normalize_plfss()

    def process(self) -> pd.DataFrame:
        # Clustering
        cluster_finder = PLFSSClusterFinder(
            amendments_df=self.plfss_pre_processor.work_amendments_df
        )
        final_clusters = cluster_finder.find_similarity_clusters(eps=0.01)
        final_clusters = cluster_finder.refine_clusters_with_exact_match(
            threshold=0.0001
        )

        # Result processing
        allotment_updater = PLFSSAllotmentUpdater(
            original_amendments_df=self.plfss_pre_processor.original_amendments_df,
            work_amendments_df=self.plfss_pre_processor.work_amendments_df,
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
    allotment_populator.preprocess()
    amendments_df = allotment_populator.process()

    amendments_df[COLUMNS_TO_OUTPUT].to_excel(OUTPUT_FILE, index=False)
    print(f"Saved result in {OUTPUT_FILE}\n")

    end_time = time.time()
    execution_time = end_time - start_time
    print("Script execution time:", execution_time, "seconds")


if __name__ == "__main__":
    main()
