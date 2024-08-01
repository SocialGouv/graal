import argparse
import os

from amendements_intelligents.utils.plfss_sheet_data_loader import (
    PLFSSSheetDataLoader,
)

DATA_FOLDER = os.getenv("DATA_FOLDER")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--excel", default=f"{DATA_FOLDER}/aled.xlsm")
    parser.add_argument("--sheet", default="PLFSS 2024")
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    plfss_excel_path = args.excel
    sheet_name = args.sheet
    output_file = args.output if args.output else f"{DATA_FOLDER}/{sheet_name}.json"

    data_extractor = PLFSSSheetDataLoader(plfss_excel_path)
    df = data_extractor.extract_sheet_data(sheet_name)
    df.to_json(output_file, orient="records", index=False)
    print(f"PLFSS extracted in {output_file}")
