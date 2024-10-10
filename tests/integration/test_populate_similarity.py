import logging
import os
from datetime import datetime
from pathlib import Path

import pandas as pd

from amendements_intelligents.populate_similarities import SimilarityHandler
from amendements_intelligents.utils.amendment_pre_processor import AmendmentPreProcessor

logging.config.fileConfig("logging.conf")


def set_timestamps(df):
    df["timestamp"] = df["date_derniere_modif"].apply(
        lambda x: int(datetime.strptime(x, "%Y-%m-%d %H:%M:%S.%f").timestamp())
        if x not in [None, ""]
        else 0
    )


def test_integration_similarity():
    ACRONYM_FILE = "tests/integration/test_data/acronym_mapping.xlsx"
    file_path = "tests/integration/test_data/test_populate_similarities.xlsx"

    old_amendments_df = pd.read_excel(file_path, sheet_name="vieux amendements")
    old_amendments_df["amdt_idx"] = range(len(old_amendments_df))
    set_timestamps(old_amendments_df)

    new_amendments_df = pd.read_excel(file_path, sheet_name="nouveaux amendements")
    new_amendments_df["amdt_idx"] = range(len(new_amendments_df))
    original_new_amendments_df = new_amendments_df.copy()

    expected_result_df = new_amendments_df.copy()

    acronym_mapping = AmendmentPreProcessor.load_acronyms_excel(ACRONYM_FILE)

    preprocessed_old_amendments_df = SimilarityHandler.preprocess_for_similarity(
        old_amendments_df, acronym_mapping
    )

    preprocessed_new_amendments_df = SimilarityHandler.preprocess_for_similarity(
        new_amendments_df, acronym_mapping
    )

    preprocessed_new_amendments_df = (
        AmendmentPreProcessor.clear_columns_to_be_overridden(
            amendments_df=preprocessed_new_amendments_df,
            columns_to_clear=["Réponse", "Sort", "Commentaires"],
        )
    )

    new_amendments_with_copies_df = SimilarityHandler.populate(
        preprocessed_old_amendments_df=preprocessed_old_amendments_df,
        preprocessed_new_amendments_df=preprocessed_new_amendments_df,
        original_new_amendments_df=original_new_amendments_df,
    )

    # COMPUTE THE DIFFERENCE

    diff_df = pd.DataFrame()
    for _, row in new_amendments_with_copies_df.iterrows():
        amdt_idx = row["amdt_idx"]
        found_response_matches = row["Réponse"]
        found_sort_matches = row["Sort"]

        expected_response_matches = expected_result_df.loc[
            (expected_result_df["amdt_idx"] == amdt_idx),
            "Réponse",
        ].values[0]

        expected_sort_matches = expected_result_df.loc[
            (expected_result_df["amdt_idx"] == amdt_idx),
            "Sort",
        ].values[0]

        if pd.isnull(expected_response_matches):
            expected_response_matches = ""
        if pd.isnull(expected_sort_matches):
            expected_sort_matches = ""

        if (
            found_response_matches != expected_response_matches
            or found_sort_matches != expected_sort_matches
        ):
            diff_df = pd.concat(
                [
                    diff_df,
                    pd.DataFrame(
                        {
                            "amdt_idx": [amdt_idx],
                            "found_response": [found_response_matches],
                            "expected_response": [expected_response_matches],
                            "found_sort": [found_sort_matches],
                            "expected_sort": [expected_sort_matches],
                        }
                    ),
                ]
            )

    if not diff_df.empty:
        diff_df.to_csv("tests/integration/test_data/diff_similarity.csv")
        logging.info(
            'Diff found and saved in "tests/integration/test_data/diff_similarity.csv"'
        )
        num_diff_rows = diff_df.shape[0]
        total_expected_rows = expected_result_df.shape[0]
        percentage_diff = (
            (num_diff_rows / total_expected_rows) * 100
            if total_expected_rows > 0
            else 0
        )

        logging.info(f"Number of differing rows: {num_diff_rows}")
        logging.info(f"Percentage of differing rows: {percentage_diff:.2f}%")

    assert diff_df.empty, f"Differences found: {len(diff_df)}"
