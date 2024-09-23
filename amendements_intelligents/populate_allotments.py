import logging
import logging.config
import os
import time

import pandas as pd

from amendements_intelligents.clustering.cluster_finder import AmendmentsClusterFinder
from amendements_intelligents.utils.allotment_updater import AllotmentUpdater
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
    def populate(
        original_amendments_df: pd.DataFrame, prepared_df: pd.DataFrame
    ) -> pd.DataFrame:
        # Clustering
        cluster_finder = AmendmentsClusterFinder(amendments_df=prepared_df)
        cluster_finder.find_similarity_clusters(eps=0.0001)
        final_clusters = cluster_finder.refine_clusters_with_distance(threshold=0.0001)

        # Result processing
        allotment_updater = AllotmentUpdater(
            original_amendments_df=original_amendments_df,
            normalized_amendments_df=prepared_df,
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

    amendments_df = AmendmentPreProcessor.load_amendments_json(
        input_files=[(INPUT_FILE, YEAR)]
    )
    acronym_mapping = AmendmentPreProcessor.load_acronyms_excel(
        acronym_file=f"{DATA_FOLDER}/acronym_mapping.xlsx"
    )
    original_amendments_df = AllotmentHandler.preprocess_json_amendments(
        amendments_df=amendments_df
    )
    prepared_df = AllotmentHandler.preprocess_amendments(
        amendments_df=amendments_df,
        acronym_mapping=acronym_mapping,
    )
    amdt_with_allotments_df = AllotmentHandler.populate(
        original_amendments_df=original_amendments_df, prepared_df=prepared_df
    )

    amdt_with_allotments_df[COLUMNS_TO_OUTPUT].to_excel(OUTPUT_FILE, index=False)
    logging.info(f"Saved result in {OUTPUT_FILE}\n")

    end_time = time.time()
    execution_time = end_time - start_time
    logging.info(f"Script execution time: {execution_time} seconds")


if __name__ == "__main__":
    main()
