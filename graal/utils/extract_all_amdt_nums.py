import logging
import logging.config
import os

from graal.utils.amendment_pre_processor import AmendmentPreProcessor

logging.config.fileConfig("logging.conf")


def main():
    DATA_FOLDER = os.getenv("DATA_FOLDER")
    # INPUT_FILE = f"{DATA_FOLDER}/input_plfss/test_no_overwrite.json"
    INPUT_FILE = f"{DATA_FOLDER}/input_plfss/lecture-senat-2024-2025-129-PO78718.json"

    amendments_df = AmendmentPreProcessor.load_amendments_json(input_files=[INPUT_FILE])
    logging.info(f"Loaded {len(amendments_df)} amendments from {INPUT_FILE}")
    amendments_df = AmendmentPreProcessor.remap_columns_in_json_amendments(
        amendments_df
    )
    unique_amdt_nums = amendments_df["Num amdt"].unique()
    OUTPUT_FILE = f"{DATA_FOLDER}/already_processed/amdt_nums_already_processed.txt"
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

    with open(OUTPUT_FILE, "w", encoding="UTF-8") as file:
        for value in unique_amdt_nums:
            file.write(f"{value}\n")

    logging.info(
        f"Extracted {len(unique_amdt_nums)} amendment numbers from {INPUT_FILE} and saved them to {OUTPUT_FILE}"
    )


if __name__ == "__main__":
    main()
