import logging
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

import pandas as pd
from pydantic import FilePath
from unidecode import unidecode

from graal.clustering.within_lecture_similarity_handler import (
    WithinLectureSimilarityHandler,
)
from graal.custom_types import ColumnName
from graal.utils.amendment_pre_processor import AmendmentPreProcessor
from graal.utils.text_utils import remove_gage_sentences

logging.config.fileConfig("logging.conf")


def set_timestamps(df):
    df["timestamp"] = df["date_derniere_modif"].apply(
        lambda x: int(datetime.strptime(x, "%Y-%m-%d %H:%M:%S.%f").timestamp())
        if x not in [None, ""]
        else 0
    )


def run_test(
    file_path: FilePath,
    clustering_similarity_thresholds: dict,
    fuzzy_match_similarity_thresholds: dict,
    similarity_threshold_overrides: dict,
    column_filtering_funcs: Optional[
        dict[ColumnName, Callable[[pd.DataFrame, pd.DataFrame], pd.DataFrame]]
    ] = None,
    column_group_by_columns: Optional[dict[ColumnName, list[ColumnName]]] = None,
    columns_to_copy_config: Optional[dict] = None,
) -> None:
    CONFIG_FILE = "tests/integration/test_data/Fichier de configuration GRAAL - Test integrations.xlsx"

    config_excel = pd.read_excel(CONFIG_FILE, sheet_name=None)

    old_amendments_df = pd.read_excel(file_path, sheet_name="vieux amendements")
    # old_amendments_df = old_amendments_df[old_amendments_df["Num amdt"].isin([3, 4])]
    old_amendments_df["amdt_idx"] = range(len(old_amendments_df))
    set_timestamps(old_amendments_df)
    old_amendments_df["Corps amdt"] = old_amendments_df["Corps amdt"].apply(
        lambda text: remove_gage_sentences(unidecode(text))
    )
    old_amendments_df["Exposé amdt"] = old_amendments_df["Exposé amdt"].apply(
        lambda text: remove_gage_sentences(unidecode(text))
    )

    new_amendments_df = pd.read_excel(file_path, sheet_name="nouveaux amendements")
    new_amendments_df["amdt_idx"] = range(len(new_amendments_df))
    # new_amendments_df = new_amendments_df[new_amendments_df["amdt_idx"] == 14]
    original_new_amendments_df = new_amendments_df.copy()

    original_new_amendments_df = AmendmentPreProcessor.clear_columns_to_be_overridden(
        amendments_df=original_new_amendments_df,
        columns_to_clear=["Réponse", "Sort", "Commentaires"],
    )

    new_amendments_df["Corps amdt"] = new_amendments_df["Corps amdt"].apply(
        lambda text: remove_gage_sentences(unidecode(text))
    )
    new_amendments_df["Exposé amdt"] = new_amendments_df["Exposé amdt"].apply(
        lambda text: remove_gage_sentences(unidecode(text))
    )

    expected_result_df = new_amendments_df.copy()

    acronym_mapping = AmendmentPreProcessor.load_acronyms(config_excel["Acronymes"])
    preprocessed_old_amendments_df = (
        WithinLectureSimilarityHandler.preprocess_for_similarity(
            old_amendments_df, acronym_mapping
        )
    )

    preprocessed_new_amendments_df = (
        WithinLectureSimilarityHandler.preprocess_for_similarity(
            new_amendments_df, acronym_mapping
        )
    )

    preprocessed_new_amendments_df = (
        AmendmentPreProcessor.clear_columns_to_be_overridden(
            amendments_df=preprocessed_new_amendments_df,
            columns_to_clear=["Réponse", "Sort", "Commentaires"],
        )
    )

    # Default configuration if none provided
    if columns_to_copy_config is None:
        columns_to_copy_config = {
            "Réponse": {"enabled": True},
            "Sort": {"enabled": True, "condition": "irrecevable"},
            "Objet": {"enabled": False},
        }

    new_amendments_with_copies_df = WithinLectureSimilarityHandler.populate(
        preprocessed_old_amendments_df=preprocessed_old_amendments_df,
        preprocessed_new_amendments_df=preprocessed_new_amendments_df,
        original_new_amendments_df=original_new_amendments_df,
        clustering_similarity_thresholds=clustering_similarity_thresholds,
        fuzzy_match_similarity_thresholds=fuzzy_match_similarity_thresholds,
        similarity_threshold_overrides=similarity_threshold_overrides,
        column_filtering_funcs=column_filtering_funcs,
        column_group_by_columns=column_group_by_columns or {},
        columns_to_copy_config=columns_to_copy_config,
    )

    # COMPUTE THE DIFFERENCE

    diff_df = pd.DataFrame()

    def get_expected_value(df: pd.DataFrame, amdt_idx: int, column: str) -> str:
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


def test_integration_similarity_expose():
    file_path = Path("tests/integration/test_data/test_similarities_expose.xlsx")
    clustering_similarity_thresholds = {
        "Exposé amdt": 0.2,
    }
    fuzzy_match_similarity_thresholds = {
        "Exposé amdt": 0.4,
    }
    similarity_threshold_overrides = {
        "Exposé amdt": {"amendement redactionnel": 0.95},
    }
    run_test(
        file_path,
        clustering_similarity_thresholds,
        fuzzy_match_similarity_thresholds,
        similarity_threshold_overrides,
    )


def test_integration_similarity_body():
    file_path = Path("tests/integration/test_data/test_similarities_body.xlsx")
    clustering_similarity_thresholds = {
        "Corps amdt": 0.4,
    }
    fuzzy_match_similarity_thresholds = {
        "Corps amdt": 0.9,
    }
    run_test(
        file_path,
        clustering_similarity_thresholds,
        fuzzy_match_similarity_thresholds,
        similarity_threshold_overrides={},
        column_filtering_funcs={
            "Corps amdt": WithinLectureSimilarityHandler.filter_old_amendments_by_project
        },
        column_group_by_columns={
            "Corps amdt": ["Num article"],
        },
    )
