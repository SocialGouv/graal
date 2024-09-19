import logging
import re

import numpy as np
import pandas as pd

from amendements_intelligents.attribution.attribution_data_loader import (
    AttributionDataLoader,
)
from amendements_intelligents.attribution.attribution_populator import (
    AttributionPopulator,
)
from amendements_intelligents.utils.amendment_pre_processor import AmendmentPreProcessor
from amendements_intelligents.utils.text_utils import AttributionTextNormalizer


def test_integration_attribute_amendments():
    test_file = "tests/integration/test_data/test_attribution_par_mot.xlsx"
    mappings_file = "tests/integration/test_data/mappings_attributions_for_tests.xlsx"
    # Make sure that random choices are always the same in this test
    np.random.seed(42)

    amendments_df = AmendmentPreProcessor.load_amendments_excel(input_file=test_file)
    amendments_df["Objet amdt"] = None
    amendments_df["Exposé amdt"] = None
    amendments_df = AmendmentPreProcessor.remap_columns_in_json_amendments(
        amendments_df=amendments_df
    )
    original_amendments_df = amendments_df.copy()
    amendments_df = AmendmentPreProcessor.clear_columns_to_be_overridden(
        amendments_df=amendments_df,
        columns_to_clear=["Affectation (email)", "Affectation (nom)"],
    )
    amendments_df["Corps amdt"] = original_amendments_df["Corps amdt"].apply(
        lambda x: AttributionTextNormalizer.normalize_text(str(x))
    )

    excel_data = pd.read_excel(mappings_file, sheet_name=None)
    codes_articles_df = AttributionDataLoader.load_codes_and_articles(excel_data)
    keywords_df = AttributionDataLoader.load_keywords(excel_data)
    attribution_mappings_when_empty = (
        AttributionDataLoader.load_default_attribution_mappings(excel_data)
    )
    name_to_email_mapping = AttributionDataLoader.load_name_email_mappings(excel_data)

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

    diff_df = pd.DataFrame()
    for _, matching_row in amendments_df.iterrows():
        num_amdt, lecture = matching_row["Num amdt"], matching_row["Lecture"]
        found_nom_matches = matching_row["Affectation (nom)"]
        found_email_matches = matching_row["Affectation (email)"]

        expected_nom_matches = original_amendments_df.loc[
            (original_amendments_df["Num amdt"] == num_amdt)
            & (original_amendments_df["Lecture"] == lecture),
            "Affectation (nom)",
        ].values[0]
        expected_email_matches = original_amendments_df.loc[
            (original_amendments_df["Num amdt"] == num_amdt)
            & (original_amendments_df["Lecture"] == lecture),
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
                            "Num amdt": [num_amdt],
                            "Lecture": [lecture],
                            "found_nom": [found_nom_matches],
                            "found_email": [found_email_matches],
                            "expected_nom": [expected_nom_matches],
                            "expected_email": [expected_email_matches],
                        }
                    ),
                ]
            )

    if not diff_df.empty:
        diff_df.to_csv("tests/integration/test_data/diff_amendments.csv")
        logging.info(
            'Diff found and saved in "tests/integration/test_data/diff_amendments.csv"'
        )

    assert diff_df.empty, f"Differences found: {len(diff_df)}"

    assert diff_df.empty, f"Differences found: {len(diff_df)}"

    assert diff_df.empty, f"Differences found: {len(diff_df)}"
