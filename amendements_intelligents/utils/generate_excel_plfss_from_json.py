"""
This script is used to generate an Excel file from a PLFSS JSON file.
"""

from amendements_intelligents.utils.plfss_pre_processor import PLFSSPreProcessor

if __name__ == "__main__":
    plfss_preproc = PLFSSPreProcessor()
    FILE_NAME = "data/PLFSS_2022"
    plfss_preproc.load_plfss_json([(f"{FILE_NAME}.json", 2022)])
    df = plfss_preproc.remap_columns_in_json_amendments()
    df.to_excel(f"{FILE_NAME}.xlsx", index=False)
