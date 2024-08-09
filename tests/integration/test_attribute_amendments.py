import pandas as pd

from amendements_intelligents.attribute_amendments import PLFSSAttributor


def test_integration_attribute_amendments():
    test_file = "tests/integration/test_data/test_attribution_par_code.xlsx"
    mappings_file = "data/mappings_attributions_aug_7.xlsx"

    processor = PLFSSAttributor()
    processor.load_data(mappings_file, test_file)

    # Match codes and articles to amendments
    best_matches_per_amdt = processor.match_codes_and_articles_to_amendments()
    matching_df = processor.filter_matching_codes_and_articles(best_matches_per_amdt)

    # Group the matching DataFrame by "Num amdt" and "Lecture"
    grouped_matching_df = processor.aggregate_matches_by_amendment(matching_df)

    # Use the newly named method to integrate the matches into the amendments DataFrame
    processor.amendments_df = processor.integrate_code_article_matches_into_amendments(
        grouped_matching_df
    )

    diff_df = pd.DataFrame()
    for _, matching_row in grouped_matching_df.iterrows():
        num_amdt, lecture = matching_row["Num amdt"], matching_row["Lecture"]
        found_matches = matching_row["Affectation (nom)"]

        expected_matches = processor.amendments_df.loc[
            (processor.amendments_df["Num amdt"] == num_amdt)
            & (processor.amendments_df["Lecture"] == lecture),
            "Affectation (nom)",
        ].values[0]

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

    assert diff_df.empty, f"Differences found: {len(diff_df)}"

    nb_with_match = len(best_matches_per_amdt)
    nb_without_match = len(processor.amendments_df) - nb_with_match
    assert nb_with_match == 18, f"Expected 18 matches, but got {nb_with_match}"
    assert (
        nb_without_match == 5
    ), f"Expected 5 without matches, but got {nb_without_match}"
