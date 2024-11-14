import logging
import logging.config
import os
import pickle
import time

import pandas as pd
from pydantic import FilePath

from amendements_intelligents.utils.amendment_pre_processor import AmendmentPreProcessor

logging.config.fileConfig("logging.conf")


def main():
    DATA_FOLDER = os.getenv("DATA_FOLDER", "data")
    ORIGINAL_INPUT_FILE = FilePath(
        f"{DATA_FOLDER}/input_plfss/lecture-an-17-325-PO420120.json"
    )
    COMMISSION_INPUT_FILE = FilePath(
        f"{DATA_FOLDER}/export_plfss_commission/export_1ere_commission_2025.json"
    )

    ATTRIBUTION_MAPPINGS_FILE = f"{DATA_FOLDER}/mappings_attributions_nov_14.xlsx"
    attribution_mappings_excel = pd.read_excel(
        ATTRIBUTION_MAPPINGS_FILE, sheet_name=None
    )

    lecture_amdt_df = AmendmentPreProcessor.load_amendments_json(
        input_files=[ORIGINAL_INPUT_FILE]
    )
    lecture_amdt_df = AmendmentPreProcessor.remap_columns_in_json_amendments(
        amendments_df=lecture_amdt_df
    )
    acronym_mapping = AmendmentPreProcessor.load_acronyms(
        attribution_mappings_excel["Acronymes"]
    )
    lecture_amdt_df = AmendmentPreProcessor.replace_acronyms(
        amendments_df=lecture_amdt_df,
        acronym_mapping=acronym_mapping,
        columns_to_normalize=["Corps amdt"],
    )
    amendments_df = AmendmentPreProcessor.load_amendments_json(
        input_files=[COMMISSION_INPUT_FILE]
    )
    amendments_df = AmendmentPreProcessor.remap_columns_in_json_amendments(
        amendments_df=amendments_df
    )
    amendments_df = amendments_df.merge(
        lecture_amdt_df[["Num amdt", "Corps amdt", "Exposé amdt"]],
        on="Num amdt",
        suffixes=("_tmp", ""),
        how="left",
    )
    amendments_df = AmendmentPreProcessor.remove_empty_rows_for_given_columns(
        amendments_df=amendments_df, columns_to_filter_with=["Corps amdt"]
    )
    amendments_df = AmendmentPreProcessor.handle_common_amendment_bodies(
        amendments_df=amendments_df
    )
    amendments_df = AmendmentPreProcessor.normalize_amendments(
        amendments_df=amendments_df, columns_to_normalize=["Corps amdt"]
    )

    filtered_amendments_df = amendments_df[
        amendments_df["Sort"].str.lower().isin(["irrecevable"])
    ]

    PREPROCESSED_INADMISSIBLE_FILE = (
        f"{DATA_FOLDER}/preprocessed/inadmissible_commission.pkl"
    )

    with open(PREPROCESSED_INADMISSIBLE_FILE, "wb") as f:
        pickle.dump(filtered_amendments_df, f)
        logging.info(
            f"Dumped pre-processed old amendments in {PREPROCESSED_INADMISSIBLE_FILE}"
        )


if __name__ == "__main__":
    start_time = time.time()
    main()
    end_time = time.time()
    logging.info(f"Inadmissible amdts preprocessed in: {end_time - start_time} seconds")
