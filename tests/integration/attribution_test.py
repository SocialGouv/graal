import logging
import random

import numpy as np
import pandas as pd
from unidecode import unidecode

from graal.attribution.project_configurations import (
    build_plfss_attribution_handler,
)
from graal.utils.amendment_pre_processor import AmendmentPreProcessor
from graal.utils.text_utils import AttributionTextNormalizer, remove_gage_sentences


def test_integration_plfss_attribution():
    TEST_FILE = "tests/integration/test_data/test_attribution.xlsx"
    CONFIG_FILE = "tests/integration/test_data/Fichier de configuration GRAAL - Test integrations.xlsx"

    # Make sure that random choices are always the same in this test
    np.random.seed(42)
    random.seed(42)

    config_excel = pd.read_excel(CONFIG_FILE, sheet_name=None)

    acronym_mapping = AmendmentPreProcessor.load_acronyms(config_excel["Acronymes"])
    amendments_df = pd.read_excel(TEST_FILE)
    # amendments_df = amendments_df[amendments_df["amdt_idx"] == 46]
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
        columns_to_clear=["Affectation (email)", "Affectation (nom)", "Entité Pilote"],
    )
    amendments_df["Corps amdt"] = amendments_df["Corps amdt"].apply(
        lambda text: remove_gage_sentences(unidecode(text))
    )
    amendments_df["Exposé amdt"] = amendments_df["Exposé amdt"].apply(
        lambda text: remove_gage_sentences(unidecode(text))
    )
    amendments_df["Corps amdt"] = original_amendments_df["Corps amdt"].apply(
        lambda x: AttributionTextNormalizer.normalize_text(str(x))
    )
    amendments_df["Exposé amdt"] = original_amendments_df["Exposé amdt"].apply(
        lambda x: AttributionTextNormalizer.normalize_text(str(x))
    )

    attribution_handler = build_plfss_attribution_handler(config_excel)

    amendments_df = attribution_handler.process_amendments(amendments_df)

    diff_df = pd.DataFrame()
    for _, matching_row in amendments_df.iterrows():
        amdt_idx = matching_row["amdt_idx"]
        found_nom_matches = matching_row["Affectation (nom)"]
        found_email_matches = matching_row["Affectation (email)"]
        found_pilot_entity_matches = matching_row["Entité Pilote"]

        expected_nom_matches = original_amendments_df.loc[
            (original_amendments_df["amdt_idx"] == amdt_idx),
            "Affectation (nom)",
        ].values[0]
        expected_email_matches = original_amendments_df.loc[
            (original_amendments_df["amdt_idx"] == amdt_idx),
            "Affectation (email)",
        ].values[0]
        expected_pilot_entity_matches = original_amendments_df.loc[
            (original_amendments_df["amdt_idx"] == amdt_idx),
            "Entité Pilote",
        ].values[0]

        if pd.isnull(expected_nom_matches):
            expected_nom_matches = ""
        if pd.isnull(expected_email_matches):
            expected_email_matches = ""
        if pd.isnull(expected_pilot_entity_matches):
            expected_pilot_entity_matches = ""

        if (
            found_nom_matches != expected_nom_matches
            or found_email_matches != expected_email_matches
            or found_pilot_entity_matches != expected_pilot_entity_matches
        ):
            diff_df = pd.concat(
                [
                    diff_df,
                    pd.DataFrame(
                        {
                            "amdt_idx": [amdt_idx],
                            "found_nom": [found_nom_matches],
                            "found_email": [found_email_matches],
                            "found_pilot_entity": [found_pilot_entity_matches],
                            "expected_nom": [expected_nom_matches],
                            "expected_email": [expected_email_matches],
                            "expected_pilot_entity": [expected_pilot_entity_matches],
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
