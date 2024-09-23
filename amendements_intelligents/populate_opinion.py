import logging
import logging.config
import os
import time

import pandas as pd

from amendements_intelligents.attribution.attribution_data_loader import (
    AttributionDataLoader,
)
from amendements_intelligents.opinion.opinion_handler import OpinionHandler
from amendements_intelligents.utils.amendment_pre_processor import AmendmentPreProcessor

logging.config.fileConfig("logging.conf")


def main():
    DATA_FOLDER = os.getenv("DATA_FOLDER", "data")
    INPUT_FILE = f"{DATA_FOLDER}/PLFSS_2024.json"
    YEAR = 2024
    OUTPUT_FILE = f"{DATA_FOLDER}/amendments_with_opinion.xlsx"
    MAPPINGS_FILE = f"{DATA_FOLDER}/mappings_attributions_sept_13.xlsx"
    attribution_mappings_excel = pd.read_excel(MAPPINGS_FILE, sheet_name=None)
    group_to_default_opinion = AttributionDataLoader.load_group_to_default_opinion(
        attribution_mappings_excel
    )
    amendments_df = AmendmentPreProcessor.load_amendments_json(
        input_files=[(INPUT_FILE, YEAR)]
    )
    amendments_df = AmendmentPreProcessor.remap_columns_in_json_amendments(
        amendments_df
    )

    opinion_populator = OpinionHandler(
        amendments_df=amendments_df,
        group_to_default_opinion=group_to_default_opinion,
    )

    amendments_df = opinion_populator.populate()
    amendments_df.to_excel(OUTPUT_FILE, index=False)
    logging.info(f"Saved amendments with opinion in {OUTPUT_FILE}\n")


if __name__ == "__main__":
    main()
