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
    AMENDMENTS_FILE = f"{DATA_FOLDER}/exports_lectures/Export PLFSS 2024/JSON/lecture-an-16-1682-PO420120.json"
    MAPPINGS_FILE = f"{DATA_FOLDER}/mappings_attributions_oct_3.xlsx"
    OUTPUT_FILE = f"{DATA_FOLDER}/test_attributions_new_format.xlsx"
    ACRONYM_FILE = f"{DATA_FOLDER}/acronym_mapping.xlsx"
    YEAR = 2024

    acronym_mapping = AmendmentPreProcessor.load_acronyms_excel(
        acronym_file=ACRONYM_FILE
    )

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
    laws_articles_df = AttributionDataLoader.load_laws_and_articles(
        attribution_mappings_excel
    )
    ordonnances_articles_df = AttributionDataLoader.load_ordonnances_and_articles(
        attribution_mappings_excel
    )
    keywords_df = AttributionDataLoader.load_keywords(
        excel_data=attribution_mappings_excel, acronym_mapping=acronym_mapping
    )
    attribution_mappings_when_empty = (
        AttributionDataLoader.load_default_attribution_mappings(
            attribution_mappings_excel
        )
    )
    name_to_email_mapping = AttributionDataLoader.load_name_email_mappings(
        attribution_mappings_excel
    )

    attributor = AttributionPopulator(
        amendments_df=amendments_df,
        attribution_mappings_when_empty=attribution_mappings_when_empty,
        codes_articles_df=codes_articles_df,
        laws_articles_df=laws_articles_df,
        ordonnances_articles_df=ordonnances_articles_df,
        keywords_df=keywords_df,
        name_to_email_mapping=name_to_email_mapping,
    )

    amendments_df = attributor.populate()

    amendments_df[
        [
            "amdt_idx",
            "Num amdt",
            "Num article",
            "auteur",
            "Groupe",
            "Corps amdt",
            "Exposé amdt",
            "Objet amdt",
            "Affectation (email)",
            "Affectation (nom)",
            "Commentaires",
        ]
    ].to_excel(OUTPUT_FILE, index=False)
    logging.info(
        f"Saved amendment with keyword and code/article affectation to: {OUTPUT_FILE}"
    )


if __name__ == "__main__":
    main()
