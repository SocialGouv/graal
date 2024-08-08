import pandas as pd

from amendements_intelligents.attribute_amendments import PLFSSAttributor


def test_integration_attribute_amendments():
    test_file = "tests/integration/test_data/test_attribution_par_code.xlsx"
    mappings_file = "data/mappings_attributions_aug_7.xlsx"
    diff_output_file = "tests/integration/test_data/diff_attribution_par_code.csv"

    processor = PLFSSAttributor()
    processor.load_mappings(mappings_file)
    processor.amendments_df = pd.read_excel(test_file)

    best_matching_codes_and_articles_per_amdt = (
        processor.find_best_matching_codes_and_articles_per_amdt()
    )
    matching_df = processor.get_rows_from_codes_and_articles_matches(
        best_matching_codes_and_articles_per_amdt
    )

    # group matching_df by "Num amdt" and "Lecture". Merge the "affectation_email" column by joining the values with a comma. Drop all other columns.
    grouped_matching_df = matching_df.groupby(["Num amdt", "Lecture"]).agg(
        {"Affectation (nom)": lambda x: ",".join(sorted(set(x)))}
    )

    diff_df = pd.DataFrame()
    for (num_amdt, lecture), affectation in grouped_matching_df.iterrows():
        found_matches = affectation["Affectation (nom)"]

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

    if len(diff_df):
        diff_df.to_csv(diff_output_file, index=False)

    assert len(diff_df) == 0

    nb_with_match = len(best_matching_codes_and_articles_per_amdt.keys())
    nb_without_match = len(processor.amendments_df["Corps amdt"]) - nb_with_match
    assert nb_with_match == 18
    assert nb_without_match == 5
