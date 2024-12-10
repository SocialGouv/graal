import logging

import numpy as np
import pandas as pd

from graal.attribution.attribution_data_loader import (
    AttributionDataLoader,
)
from graal.attribution.attribution_populator import (
    AttributionPopulator,
)
from graal.utils.amendment_pre_processor import AmendmentPreProcessor
from graal.utils.text_utils import AttributionTextNormalizer


def test_integration_attribute_amendments():
    TEST_FILE = "tests/integration/test_data/test_attribution.xlsx"
    CONFIG_FILE = "tests/integration/test_data/mappings_attributions_for_tests.xlsx"

    # Make sure that random choices are always the same in this test
    np.random.seed(42)

    config_excel = pd.read_excel(CONFIG_FILE, sheet_name=None)

    acronym_mapping = AmendmentPreProcessor.load_acronyms(config_excel["Acronymes"])
    amendments_df = pd.read_excel(TEST_FILE)
    # amendments_df = amendments_df[amendments_df["amdt_idx"] == 24]
    amendments_df = AmendmentPreProcessor.remap_columns_in_json_amendments(
        amendments_df=amendments_df
    )
    amendments_df = AmendmentPreProcessor.replace_acronyms(
        amendments_df=amendments_df,
        acronym_mapping=acronym_mapping,
        columns_to_normalize=["Exposé amdt", "Corps amdt"],
    )
    original_amendments_df = amendments_df.copy()
    amendments_df = AmendmentPreProcessor.clear_columns_to_be_overridden(
        amendments_df=amendments_df,
        columns_to_clear=["Affectation (email)", "Affectation (nom)"],
    )
    amendments_df["Corps amdt"] = original_amendments_df["Corps amdt"].apply(
        lambda x: AttributionTextNormalizer.normalize_text(str(x))
    )
    amendments_df["Exposé amdt"] = original_amendments_df["Exposé amdt"].apply(
        lambda x: AttributionTextNormalizer.normalize_text(str(x))
    )

    codes_articles_df = AttributionDataLoader.load_codes_and_articles(config_excel)
    laws_articles_df = AttributionDataLoader.load_laws_and_articles(config_excel)
    ordonnances_articles_df = AttributionDataLoader.load_ordonnances_and_articles(
        config_excel
    )
    keywords_df = AttributionDataLoader.load_keywords(
        excel_data=config_excel, acronym_mapping=acronym_mapping
    )
    attribution_mappings_when_empty = (
        AttributionDataLoader.load_default_attribution_mappings(config_excel)
    )
    name_to_email_mapping = AttributionDataLoader.load_name_email_mappings(config_excel)

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

    diff_df = pd.DataFrame()
    for _, matching_row in amendments_df.iterrows():
        amdt_idx = matching_row["amdt_idx"]
        found_nom_matches = matching_row["Affectation (nom)"]
        found_email_matches = matching_row["Affectation (email)"]

        expected_nom_matches = original_amendments_df.loc[
            (original_amendments_df["amdt_idx"] == amdt_idx),
            "Affectation (nom)",
        ].values[0]
        expected_email_matches = original_amendments_df.loc[
            (original_amendments_df["amdt_idx"] == amdt_idx),
            "Affectation (email)",
        ].values[0]

        if pd.isnull(expected_nom_matches):
            expected_nom_matches = ""
        if pd.isnull(expected_email_matches):
            expected_email_matches = ""

        if (
            found_nom_matches != expected_nom_matches
            or found_email_matches != expected_email_matches
        ):
            diff_df = pd.concat(
                [
                    diff_df,
                    pd.DataFrame(
                        {
                            "amdt_idx": [amdt_idx],
                            "found_nom": [found_nom_matches],
                            "found_email": [found_email_matches],
                            "expected_nom": [expected_nom_matches],
                            "expected_email": [expected_email_matches],
                        }
                    ),
                ]
            )

    if not diff_df.empty:
        diff_df.to_csv("tests/integration/test_data/diff_attribution.csv")
        logging.info(
            'Diff found and saved in "tests/integration/test_data/diff_attribution.csv"'
        )

    assert diff_df.empty, f"Differences found: {len(diff_df)}"
