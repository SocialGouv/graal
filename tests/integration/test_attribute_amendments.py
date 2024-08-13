import pandas as pd

from amendements_intelligents.attribute_amendments import (
    PLFSSAttributor,
    update_affectation,
)


def test_integration_attribute_amendments():
    test_file = "tests/integration/test_data/test_attribution_par_mot.xlsx"
    mappings_file = "tests/integration/test_data/mappings_attributions_for_tests.xlsx"

    attributor = PLFSSAttributor()
    attributor.load_data(mappings_file, test_file)

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
    amendments_df.set_index(["Num amdt", "Lecture"], inplace=True)

    amendments_df["Affectation (nom)"] = amendments_df["Affectation (nom)"].str.split(
        ","
    )

    amendments_df["Affectation (nom)"] = amendments_df.apply(
        update_affectation, axis=1, keyword_matches=keyword_matches_df
    )

    amendments_df.reset_index(inplace=True)

    diff_df = pd.DataFrame()
    for _, matching_row in amendments_df.iterrows():
        num_amdt, lecture = matching_row["Num amdt"], matching_row["Lecture"]
        found_matches = matching_row["Affectation (nom)"]

        expected_matches = attributor.amendments_df.loc[
            (attributor.amendments_df["Num amdt"] == num_amdt)
            & (attributor.amendments_df["Lecture"] == lecture),
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
    nb_without_match = len(attributor.amendments_df) - nb_with_match
    assert nb_with_match == 21, f"Expected 21 matches, but got {nb_with_match}"
    assert (
        nb_without_match == 3
    ), f"Expected 3 without matches, but got {nb_without_match}"
