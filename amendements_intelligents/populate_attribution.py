import logging
import logging.config
import os
import re

import pandas as pd

from amendements_intelligents.attribution.attribution_data_loader import (
    AttributionDataLoader,
)
from amendements_intelligents.attribution.attribution_populator import (
    AttributionPopulator,
)
from amendements_intelligents.utils.amendment_pre_processor import AmendmentPreProcessor
from amendements_intelligents.utils.text_utils import AttributionTextNormalizer

logging.config.fileConfig("logging.conf")


def main():
    DATA_FOLDER = os.getenv("DATA_FOLDER")
    AMENDMENTS_FILE = f"{DATA_FOLDER}/PLFSS_2024.json"
    MAPPINGS_FILE = f"{DATA_FOLDER}/mappings_attributions_sept_12.xlsx"
    OUTPUT_FILE = f"{DATA_FOLDER}/amendments_with_keyword_and_code_art_affectation.xlsx"
    YEAR = 2024

    amendments_df = AmendmentPreProcessor.load_amendments_json(
        input_files=[(AMENDMENTS_FILE, YEAR)]
    )
    amendments_df = AmendmentPreProcessor.remap_columns_in_json_amendments(
        amendments_df
    )
    amendments_df = AmendmentPreProcessor.clear_columns_to_be_overridden(
        amendments_df=amendments_df,
        columns_to_clear=["Affectation (email)", "Affectation (nom)"],
    )

    amendments_df["Corps amdt"] = amendments_df["Corps amdt"].apply(
        lambda x: AttributionTextNormalizer.normalize_text(str(x))
    )

    attribution_mappings_excel = pd.read_excel(MAPPINGS_FILE, sheet_name=None)
    codes_articles_df = AttributionDataLoader.load_codes_and_articles(
        attribution_mappings_excel
    )
    keywords_df = AttributionDataLoader.load_keywords(attribution_mappings_excel)
    attribution_mappings_when_empty = (
        AttributionDataLoader.load_attribution_mappings_when_empty(
            attribution_mappings_excel
        )
    )
    name_to_email_mapping = AttributionDataLoader.load_name_email_mappings(
        attribution_mappings_excel
    )

    codes_set = set(codes_articles_df["Code"])
    max_code_length = codes_articles_df["Code"].str.len().max()
    articles_set = set(codes_articles_df["Articles"])
    pattern = re.compile(r"(?:\d+(?:-\d+)*)(?:\s(.+))?")
    latin_ordinals_set = {
        match.group(1)
        for article in articles_set
        if (match := pattern.match(article)) and match.group(1)
    }

    attributor = AttributionPopulator(
        amendments_df=amendments_df,
        articles_set=articles_set,
        attribution_mappings_when_empty=attribution_mappings_when_empty,
        codes_articles_df=codes_articles_df,
        codes_set=codes_set,
        keywords_df=keywords_df,
        latin_ordinals_set=latin_ordinals_set,
        max_code_length=max_code_length,
        name_to_email_mapping=name_to_email_mapping,
    )

    amendments_df = attributor.populate()

    amendments_df.to_excel(OUTPUT_FILE, index=False)
    logging.info(
        f"Saved amendment with keyword and code/article affectation to: {OUTPUT_FILE}"
    )


if __name__ == "__main__":
    main()
if __name__ == "__main__":
    main()
if __name__ == "__main__":
    main()
