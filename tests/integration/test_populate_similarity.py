import logging
from datetime import datetime

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
    # old_amendments_df = old_amendments_df[old_amendments_df["Num amdt"].isin([3, 4])]
    old_amendments_df["amdt_idx"] = range(len(old_amendments_df))
    set_timestamps(old_amendments_df)

    new_amendments_df = pd.read_excel(file_path, sheet_name="nouveaux amendements")
    new_amendments_df["amdt_idx"] = range(len(new_amendments_df))
    # new_amendments_df = new_amendments_df[new_amendments_df["amdt_idx"] == 14]
    original_new_amendments_df = new_amendments_df.copy()

    original_new_amendments_df = AmendmentPreProcessor.clear_columns_to_be_overridden(
        amendments_df=original_new_amendments_df,
        columns_to_clear=["Réponse", "Sort", "Commentaires"],
    )

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
        clustering_threshold=0.2,
    )

    # COMPUTE THE DIFFERENCE

    diff_df = pd.DataFrame()

    def get_expected_value(df, amdt_idx, column):
        value = df.loc[df["amdt_idx"] == amdt_idx, column].values[0]
        return "" if pd.isnull(value) else value

    for _, row in new_amendments_with_copies_df.iterrows():
        amdt_idx = row["amdt_idx"]

        found_values = {
            "Réponse": row["Réponse"].strip() if not pd.isnull(row["Réponse"]) else "",
            "Sort": row["Sort"].strip() if not pd.isnull(row["Sort"]) else "",
            "Commentaires": row["Commentaires"].strip()
            if not pd.isnull(row["Commentaires"])
            else "",
        }

        expected_values = {
            column: get_expected_value(expected_result_df, amdt_idx, column).strip()
            for column in ["Réponse", "Sort", "Commentaires"]
        }

        if any(
            found_values[col] != expected_values[col]
            for col in ["Réponse", "Sort", "Commentaires"]
        ):
            diff_df = pd.concat(
                [
                    diff_df,
                    pd.DataFrame(
                        {
                            "amdt_idx": [amdt_idx],
                            **{
                                f"found_{col.lower()}": [found_values[col]]
                                for col in found_values
                            },
                            **{
                                f"expected_{col.lower()}": [expected_values[col]]
                                for col in expected_values
                            },
                        }
                    ),
                ]
            )
            for col in ["Réponse", "Sort", "Commentaires"]:
                if found_values[col] != expected_values[col]:
                    num_amdt = new_amendments_with_copies_df.loc[
                        new_amendments_with_copies_df["amdt_idx"] == amdt_idx
                    ]["Num amdt"].values[0]
                    logging.warning(
                        f"Difference found in column '{col}' for amdt_idx {amdt_idx} (Num amdt: {num_amdt}):\nFound '{col}': {found_values[col]}\nExpected '{col}': {expected_values[col]}"
                    )

    if not diff_df.empty:
        num_diff_rows = diff_df.shape[0]
        total_expected_rows = expected_result_df.shape[0]
        percentage_diff = (
            (num_diff_rows / total_expected_rows) * 100
            if total_expected_rows > 0
            else 0
        )

        logging.warning(f"Number of differing rows: {num_diff_rows}")
        logging.warning(f"Percentage of differing rows: {percentage_diff:.2f}%")

    assert diff_df.empty, f"Differences found: {len(diff_df)}"
