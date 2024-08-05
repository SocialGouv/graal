"""
This script is used to generate a sample of amendments from a PLFSS dataset.

That sample can be used to test different LLMs to generate summaries of the amendments for example.
"""

import os

from amendements_intelligents.utils.plfss_pre_processor import PLFSSPreProcessor
from amendements_intelligents.utils.plfss_text_utils import extract_plain_text_from_html

DATA_FOLDER = os.getenv("DATA_FOLDER", "data")
PLFSS_YEAR = 2024
INPUT_FILE_PLFSS = f"{DATA_FOLDER}/PLFSS_{PLFSS_YEAR}.json"
N_SAMPLES = 50

if __name__ == "__main__":
    preproc = PLFSSPreProcessor()
    preproc.load_plfss(INPUT_FILE_PLFSS)
    preproc.clean_up_original_amendments()

    df = preproc.original_amendments_df.copy()
    df = df[df["Exposé amdt"].str.len() > 50]

    df = df.sample(N_SAMPLES)

    df["objet"] = df["objet"].apply(extract_plain_text_from_html)
    df.rename(columns={"objet": "Objet (Expert)"}, inplace=True)
    df = df[["Num amdt", "Lecture", "Objet (Expert)", "Exposé amdt", "Corps amdt"]]
    df.to_excel(f"{DATA_FOLDER}/sample_aug_plfss_{PLFSS_YEAR}.xlsx", index=False)
