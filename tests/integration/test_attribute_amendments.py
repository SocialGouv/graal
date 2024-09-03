import re

import pandas as pd

from amendements_intelligents.attribution.attribution_data_loader import (
    AttributionDataLoader,
)
from amendements_intelligents.attribution.plfss_attributor import PLFSSAttributor
from amendements_intelligents.populate_attribution import AffectationUpdater
from amendements_intelligents.utils.plfss_pre_processor import PLFSSPreProcessor
from amendements_intelligents.utils.plfss_text_utils import AttributionTextNormalizer


def test_integration_attribute_amendments():
    test_file = "tests/integration/test_data/test_attribution_par_mot.xlsx"
    mappings_file = "tests/integration/test_data/mappings_attributions_for_tests.xlsx"

    amendments_df = PLFSSPreProcessor.load_plfss_excel(input_file=test_file)
    amendments_df["Objet"] = None
    amendments_df["Exposé amdt"] = None
    amendments_df = PLFSSPreProcessor.remap_columns_in_json_amendments(
        amendments_df=amendments_df
    )
    original_amendments_df = amendments_df.copy()
    amendments_df = PLFSSPreProcessor.prepare_amendments_columns(
        amendments_df=amendments_df
    )
    amendments_df["Corps amdt"] = amendments_df["Corps amdt"].apply(
        lambda x: AttributionTextNormalizer.normalize_text(str(x))
    )

    excel_data = pd.read_excel(mappings_file, sheet_name=None)
    codes_articles_df = AttributionDataLoader.load_codes_and_articles(excel_data)
    keywords_df = AttributionDataLoader.load_keywords(excel_data)

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

    # Match codes and articles to amendments
    best_matches_per_amdt = attributor.match_codes_and_articles_to_amendments()
    matching_df = attributor.filter_matching_codes_and_articles(best_matches_per_amdt)

    # Group the matching DataFrame by "Num amdt" and "Lecture"
    grouped_matching_df = attributor.aggregate_matches_by_amendment(matching_df)

    # Use the newly named method to integrate the matches into the amendments DataFrame
    amendments_df = attributor.integrate_code_article_matches_into_amendments(
        grouped_matching_df
    )

    # Step 2: Match keywords to amendments
    keyword_matches_df = attributor.match_keywords_to_amendments(threshold=95)

    keyword_matches_df.set_index(["Num amdt", "Lecture"], inplace=True)
    keyword_matches_df = keyword_matches_df.sort_index()
    amendments_df.set_index(["Num amdt", "Lecture"], inplace=True)

    amendments_df["Affectation (nom)"] = amendments_df["Affectation (nom)"].str.split(
        ","
    )

    amendments_df["Affectation (nom)"] = amendments_df.apply(
        AffectationUpdater.update, axis=1, keyword_matches_df=keyword_matches_df
    )

    amendments_df.reset_index(inplace=True)

    diff_df = pd.DataFrame()
    for _, matching_row in amendments_df.iterrows():
        num_amdt, lecture = matching_row["Num amdt"], matching_row["Lecture"]
        found_matches = matching_row["Affectation (nom)"]

        expected_matches = original_amendments_df.loc[
            (original_amendments_df["Num amdt"] == num_amdt)
            & (original_amendments_df["Lecture"] == lecture),
            "Affectation (nom)",
        ].values[0]

        if pd.isnull(expected_matches):
            expected_matches = ""

        if found_matches != expected_matches:
            diff_df = pd.concat(
                [
                    diff_df,
                    pd.DataFrame(
                        {
                            "Num amdt": [num_amdt],
                            "Lecture": [lecture],
                            "found": [found_matches],
                            "expected": [expected_matches],
                        }
                    ),
                ]
            )

    if not diff_df.empty:
        print(diff_df)
        diff_df.to_csv("tests/integration/test_data/diff_amendments.csv")

    assert diff_df.empty, f"Differences found: {len(diff_df)}"

    nb_with_match = len(best_matches_per_amdt)
    nb_without_match = len(original_amendments_df) - nb_with_match
    assert nb_with_match == 21, f"Expected 21 matches, but got {nb_with_match}"
    assert (
        nb_without_match == 3
    ), f"Expected 3 without matches, but got {nb_without_match}"
