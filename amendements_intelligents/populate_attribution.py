import logging
import logging.config
import re

import pandas as pd

from amendements_intelligents.attribution.attribution_data_loader import (
    AttributionDataLoader,
)
from amendements_intelligents.attribution.plfss_attributor import PLFSSAttributor
from amendements_intelligents.utils.plfss_pre_processor import PLFSSPreProcessor
from amendements_intelligents.utils.plfss_text_utils import AttributionTextNormalizer

logging.config.fileConfig("logging.conf")


def main():
    amendments_file = "data/PLFSS_2024.json"
    MAPPINGS_FILE = "data/mappings_attributions_aug_9.xlsx"
    output_file = "data/amendments_with_keyword_and_code_art_affectation.xlsx"
    YEAR = 2024

    amendments_df = PLFSSPreProcessor.load_plfss_json(
        input_files=[(amendments_file, YEAR)]
    )
    amendments_df = PLFSSPreProcessor.remap_columns_in_json_amendments(amendments_df)
    amendments_df = PLFSSPreProcessor.prepare_amendments_columns(amendments_df)

    amendments_df["Corps amdt"] = amendments_df["Corps amdt orig"].apply(
        lambda x: AttributionTextNormalizer.normalize_text(str(x))
    )

    attribution_mappings_excel = pd.read_excel(MAPPINGS_FILE, sheet_name=None)
    codes_articles_df = AttributionDataLoader.load_codes_and_articles(
        attribution_mappings_excel
    )
    keywords_df = AttributionDataLoader.load_keywords(attribution_mappings_excel)

    codes_set = set(codes_articles_df["Code"])
    max_code_length = codes_articles_df["Code"].str.len().max()
    articles_set = set(codes_articles_df["Articles"])
    pattern = re.compile(r"(?:\d+(?:-\d+)*)(?:\s(.+))?")
    latin_ordinals_set = {
        match.group(1)
        for article in articles_set
        if (match := pattern.match(article)) and match.group(1)
    }

    attributor = PLFSSAttributor(
        amendments_df=amendments_df,
        articles_set=articles_set,
        codes_articles_df=codes_articles_df,
        codes_set=codes_set,
        keywords_df=keywords_df,
        latin_ordinals_set=latin_ordinals_set,
        max_code_length=max_code_length,
    )

    amendments_df = attributor.populate()

    amendments_df.to_excel(output_file, index=False)
    logging.info(
        f"Saved amendment with keyword and code/article affectation to: {output_file}"
    )


if __name__ == "__main__":
    main()
