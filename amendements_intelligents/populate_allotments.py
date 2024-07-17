import os
import time

import pandas as pd
from pydantic import FilePath

from amendements_intelligents.clustering.plfss_cluster_finder import PLFSSClusterFinder
from amendements_intelligents.data_handlers.plfss_allotment_updater import (
    PLFSSAllotmentUpdater,
)
from amendements_intelligents.data_handlers.plfss_data_processor import (
    PLFSSDataProcessor,
)


class PLFSSAllotmentPopulator:
    def __init__(self, input_file: FilePath) -> None:
        self.input_file = input_file

    def process(self) -> pd.DataFrame:
        # Data processing
        plfss_data_processor = PLFSSDataProcessor(input_file=self.input_file)
        plfss_data_processor.load_plfss()
        preprocessed_amendments_df = plfss_data_processor.preprocess_plfss()

        # Clustering
        cluster_finder = PLFSSClusterFinder(
            preprocessed_amendments_df=preprocessed_amendments_df
        )
        final_clusters = cluster_finder.find_similarity_clusters(eps=0.01)
        final_clusters = cluster_finder.refine_clusters_with_exact_match(
            threshold=0.0001
        )

        # Result processing
        allotment_updater = PLFSSAllotmentUpdater(
            amendments_df=plfss_data_processor.amendments_df,
            preprocessed_amendments_df=plfss_data_processor.preprocessed_amendments_df,
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

    allotment_populator = PLFSSAllotmentPopulator(input_file=INPUT_FILE)
    amendments_df = allotment_populator.process()

    amendments_df[COLUMNS_TO_OUTPUT].to_excel(OUTPUT_FILE, index=False)
    print(f"Saved result in {OUTPUT_FILE}\n")

    end_time = time.time()
    execution_time = end_time - start_time
    print("Script execution time:", execution_time, "seconds")


if __name__ == "__main__":
    main()
