import textwrap
from typing import Callable, Optional

import pandas as pd
import pytest

from graal.similarities.similarity_search_handler import (
    SimilaritySearchHandler,
)


@pytest.fixture
def sample_data():
    old_amendments_df = pd.DataFrame(
        {
            "Num amdt": [1, 2, 3],
            "amdt_idx": [1, 2, 3],
            "Lecture": ["A", "B", "C"],
            "Organe": ["Organe 1", "Organe 2", "Organe 3"],
            "Réponse": ["Response 1", "Response 2", "Response 3"],
            "Sort": ["Sort 1", "Irrecevable 123", "Sort 3"],
            "origin_project": ["PLFSS 2022", "PLACSS 2023", "PLFSS 2023"],
        }
    )
    closest_amdts = {
        97: {
            "best_matching_doc_amdt_idx": 1,
            "best_matching_doc_lecture": "A",
            "column_used_for_comparison": "Exposé amdt",
        },
        98: {
            "best_matching_doc_amdt_idx": 2,
            "best_matching_doc_lecture": "B",
            "column_used_for_comparison": "Exposé amdt",
        },
        99: {
            "best_matching_doc_amdt_idx": 3,
            "column_used_for_comparison": "Exposé amdt",
        },
    }
    target_df = pd.DataFrame(
        {
            "Num amdt": [1, 2, 3],
            "amdt_idx": [97, 98, 99],
            "Lecture": ["A", "B", "C"],
            "Réponse": ["", "", ""],
            "Commentaires": ["", "", ""],
            "Sort": ["", "", ""],
        }
    )
    return old_amendments_df, closest_amdts, target_df


def test_copy_matches_to_amendments_df(sample_data):
    old_amendments_df, closest_amdts, target_df = sample_data
    # Use default configuration
    columns_config = {
        "Réponse": {"enabled": True},
        "Sort": {"enabled": True, "condition": "irrecevable"},
        "Objet": {"enabled": False},
    }
    result_df = SimilaritySearchHandler.copy_matches_to_amendments_df(
        target_df=target_df,
        old_amendments_df=old_amendments_df,
        closest_amdts=closest_amdts,
        columns_config=columns_config,
    )

    assert result_df.loc[0, "Réponse"] == "Response 1"
    assert (
        result_df.loc[0, "Commentaires"]
        == textwrap.dedent("""
        Copie de Réponse, Sort depuis : PLFSS 2022
        Numéro d'amendement : 1
        Lecture : A
        Organe : Organe 1
        Colonne similaire : Exposé amdt
        """).strip()
    )
    assert result_df.loc[0, "Sort"] == ""

    assert result_df.loc[1, "Réponse"] == "Response 2"
    assert (
        result_df.loc[1, "Commentaires"]
        == textwrap.dedent("""
        Copie de Réponse, Sort depuis : PLACSS 2023
        Numéro d'amendement : 2
        Lecture : B
        Organe : Organe 2
        Colonne similaire : Exposé amdt
        Sort copié : Irrecevable 123
        """).strip()
    )
    assert result_df.loc[1, "Sort"] == "Irrecevable 123"

    assert result_df.loc[2, "Réponse"] == "Response 3"
    assert (
        result_df.loc[2, "Commentaires"]
        == textwrap.dedent("""
        Copie de Réponse, Sort depuis : PLFSS 2023
        Numéro d'amendement : 3
        Lecture : C
        Organe : Organe 3
        Colonne similaire : Exposé amdt
        """).strip()
    )
    assert result_df.loc[2, "Sort"] == ""


def test_copy_matches_to_amendments_df_with_custom_config(sample_data):
    old_amendments_df, closest_amdts, target_df = sample_data

    # Add Objet column to test data
    old_amendments_df["Objet"] = ["Objet 1", "Objet 2", "Objet 3"]
    target_df["Objet"] = ["", "", ""]

    # Test with custom configuration - only copy Objet, disable Réponse and Sort
    columns_config = {
        "Réponse": {"enabled": False},
        "Sort": {"enabled": False},
        "Objet": {"enabled": True},
    }

    result_df = SimilaritySearchHandler.copy_matches_to_amendments_df(
        target_df=target_df,
        old_amendments_df=old_amendments_df,
        closest_amdts=closest_amdts,
        columns_config=columns_config,
    )

    # Verify Objet was copied but not Réponse or Sort
    assert result_df.loc[0, "Objet"] == "Objet 1"
    assert result_df.loc[1, "Objet"] == "Objet 2"
    assert result_df.loc[2, "Objet"] == "Objet 3"

    assert result_df.loc[0, "Réponse"] == ""
    assert result_df.loc[1, "Réponse"] == ""
    assert result_df.loc[2, "Réponse"] == ""

    assert result_df.loc[0, "Sort"] == ""
    assert result_df.loc[1, "Sort"] == ""
    assert result_df.loc[2, "Sort"] == ""


def test_populate():
    preprocessed_new_amendments_df = pd.DataFrame(
        {
            "Num amdt": [1, 2, 3],
            "amdt_idx": [97, 98, 99],
            "Lecture": ["A", "B", "C"],
            "Organe": ["Organe 1", "Organe 2", "Organe 3"],
            "Exposé amdt": ["Exposé 1", "Exposé 2", "Not the same Exposé 3"],
            "Corps amdt": ["Corps 1", "Corps 2", "Corps 3"],
            "Commentaires": ["", "", ""],
            "Réponse": ["", "", ""],
            "Sort": ["", "", ""],
            "timestamp": [0, 0, 0],
            "origin_project": ["PLFSS 2010", "PLACSS 1900", "PLFSS 1963"],
        }
    )

    original_new_amendments_df = preprocessed_new_amendments_df.copy()
    preprocessed_old_amendments_df = pd.DataFrame(
        {
            "Num amdt": [1, 2, 3],
            "amdt_idx": [1, 2, 3],
            "Lecture": ["A", "B", "C"],
            "Objet": ["Objet 1", "Objet 2", "Objet 3"],
            "Organe": ["Organe 1", "Organe 2", "Organe 3"],
            "Réponse": ["Response 1", "Response 2", "Response 3"],
            "Sort": ["Sort 1", "Irrecevable 123", "Sort 3"],
            "Exposé amdt": ["Exposé 1", "Exposé 2", "Exposé 3"],
            "Corps amdt": ["Corps 1", "Corps 2", "Corps 3"],
            "timestamp": [0, 0, 0],
            "origin_project": ["PLFSS 2024", "PLACSS 2020", "PLFSS 1988"],
        }
    )

    clustering_similarity_thresholds: dict[str, float] = {
        "Exposé amdt": 1.0,
        "Corps amdt": 1.0,
    }
    fuzzy_match_similarity_thresholds: dict[str, float] = {
        "Exposé amdt": 1.0,
        "Corps amdt": 1.0,
    }
    similarity_threshold_overrides: dict[str, dict[str, float]] = {}

    # Use default configuration
    columns_to_copy_config = {
        "Réponse": {"enabled": True},
        "Sort": {"enabled": True, "condition": "irrecevable"},
        "Objet": {"enabled": True},
    }

    result_df = SimilaritySearchHandler.populate(
        preprocessed_old_amendments_df=preprocessed_old_amendments_df,
        preprocessed_new_amendments_df=preprocessed_new_amendments_df,
        original_new_amendments_df=original_new_amendments_df,
        clustering_similarity_thresholds=clustering_similarity_thresholds,
        fuzzy_match_similarity_thresholds=fuzzy_match_similarity_thresholds,
        similarity_threshold_overrides=similarity_threshold_overrides,
        column_group_by_columns={},
        columns_to_copy_config=columns_to_copy_config,
    )

    assert (
        result_df.loc[0, "Commentaires"]
        == textwrap.dedent("""
        Copie de Réponse, Sort, Objet depuis : PLFSS 2024
        Numéro d'amendement : 1
        Lecture : A
        Organe : Organe 1
        Colonne similaire : Exposé amdt
        """).strip()
    )
    assert (
        result_df.loc[1, "Commentaires"]
        == textwrap.dedent("""
        Copie de Réponse, Sort, Objet depuis : PLACSS 2020
        Numéro d'amendement : 2
        Lecture : B
        Organe : Organe 2
        Colonne similaire : Exposé amdt
        Sort copié : Irrecevable 123
        """).strip()
    )
    assert (
        result_df.loc[2, "Commentaires"]
        == textwrap.dedent("""
        Copie de Réponse, Sort, Objet depuis : PLFSS 1988
        Numéro d'amendement : 3
        Lecture : C
        Organe : Organe 3
        Colonne similaire : Corps amdt
        """).strip()
    )

    assert result_df.loc[0, "Réponse"] == "Response 1"
    assert result_df.loc[1, "Réponse"] == "Response 2"
    assert result_df.loc[2, "Réponse"] == "Response 3"

    assert result_df.loc[0, "Sort"] == ""
    assert result_df.loc[1, "Sort"] == "Irrecevable 123"
    assert result_df.loc[2, "Sort"] == ""

    assert result_df.loc[0, "Objet"] == "Objet 1"
    assert result_df.loc[1, "Objet"] == "Objet 2"
    assert result_df.loc[2, "Objet"] == "Objet 3"


def test_copy_matches_with_should_overwrite_false(sample_data):
    """Test that should_overwrite=False preserves existing values."""
    old_amendments_df, closest_amdts, target_df = sample_data

    # Set existing values in target
    target_df.loc[0, "Réponse"] = "Existing Response"
    target_df.loc[1, "Réponse"] = ""  # Empty, should be filled
    target_df.loc[2, "Réponse"] = "   "  # Whitespace only, should be filled

    columns_config = {
        "Réponse": {"enabled": True},
        "Sort": {"enabled": True, "condition": "irrecevable"},
    }

    result_df = SimilaritySearchHandler.copy_matches_to_amendments_df(
        target_df=target_df,
        old_amendments_df=old_amendments_df,
        closest_amdts=closest_amdts,
        columns_config=columns_config,
        should_overwrite=False,
    )

    # First row should keep existing value
    assert result_df.loc[0, "Réponse"] == "Existing Response"

    # Second row should be filled (was empty)
    assert result_df.loc[1, "Réponse"] == "Response 2"

    # Third row should be filled (was whitespace only)
    assert result_df.loc[2, "Réponse"] == "Response 3"


def test_copy_matches_with_should_overwrite_true(sample_data):
    """Test that should_overwrite=True overwrites existing values."""
    old_amendments_df, closest_amdts, target_df = sample_data

    # Set existing values in target
    target_df.loc[0, "Réponse"] = "Existing Response"
    target_df.loc[1, "Réponse"] = "Another Existing"

    columns_config = {
        "Réponse": {"enabled": True},
        "Sort": {"enabled": False},
    }

    result_df = SimilaritySearchHandler.copy_matches_to_amendments_df(
        target_df=target_df,
        old_amendments_df=old_amendments_df,
        closest_amdts=closest_amdts,
        columns_config=columns_config,
        should_overwrite=True,  # Default behavior
    )

    # All values should be overwritten
    assert result_df.loc[0, "Réponse"] == "Response 1"
    assert result_df.loc[1, "Réponse"] == "Response 2"
    assert result_df.loc[2, "Réponse"] == "Response 3"


def test_copy_matches_with_should_overwrite_false_handles_none_and_nan(sample_data):
    """Test that should_overwrite=False correctly handles None and NaN values."""
    old_amendments_df, closest_amdts, target_df = sample_data

    # Set various empty-like values
    target_df.loc[0, "Réponse"] = None
    target_df.loc[1, "Réponse"] = pd.NA
    target_df.loc[2, "Réponse"] = float("nan")

    columns_config = {
        "Réponse": {"enabled": True},
    }

    result_df = SimilaritySearchHandler.copy_matches_to_amendments_df(
        target_df=target_df,
        old_amendments_df=old_amendments_df,
        closest_amdts=closest_amdts,
        columns_config=columns_config,
        should_overwrite=False,
    )

    # All should be filled as they're empty
    assert result_df.loc[0, "Réponse"] == "Response 1"
    assert result_df.loc[1, "Réponse"] == "Response 2"
    assert result_df.loc[2, "Réponse"] == "Response 3"


def test_populate_same_body_but_different_project_should_not_match():
    preprocessed_new_amendments_df = pd.DataFrame(
        {
            "Num amdt": [1, 2],
            "amdt_idx": [97, 98],
            "Lecture": ["A", "A"],
            "Corps amdt": ["Corps 1", "Corps 2"],
            "Commentaires": ["", ""],
            "Réponse": ["", ""],
            "Sort": ["", ""],
            "timestamp": [0, 0],
            "origin_project": ["PLFSS 2024", "PLFSS 2024"],
        }
    )

    original_new_amendments_df = preprocessed_new_amendments_df.copy()

    preprocessed_old_amendments_df = pd.DataFrame(
        {
            "Num amdt": [1, 2, 3],
            "amdt_idx": [1, 2, 3],
            "Lecture": ["A", "A", "A"],
            "Organe": ["Organe 1", "Organe 2", "Organe 3"],
            "Corps amdt": ["Corps 1", "Corps 2", "Corps 2"],
            "Sort": ["Sort 1", "Sort 2", "Sort 3"],
            "Réponse": ["Response 1", "Response 2", "Response 3"],
            "timestamp": [1737587137, 0, 0],
            "origin_project": ["PLFSS 2024", "PLACSS 2024", "PLFSS 2025"],
        }
    )

    clustering_similarity_thresholds: dict[str, float] = {
        "Corps amdt": 1.0,
    }
    fuzzy_match_similarity_thresholds: dict[str, float] = {
        "Corps amdt": 1.0,
    }
    similarity_threshold_overrides: dict[str, dict[str, float]] = {}

    column_filtering_funcs: Optional[
        dict[str, Callable[[pd.DataFrame, pd.DataFrame], pd.DataFrame]]
    ] = {
        "Corps amdt": SimilaritySearchHandler.filter_old_amendments_by_project,
    }

    # Use default configuration
    columns_to_copy_config = {
        "Réponse": {"enabled": True},
        "Sort": {"enabled": True, "condition": "irrecevable"},
        "Objet": {"enabled": False},
    }

    result_df = SimilaritySearchHandler.populate(
        preprocessed_old_amendments_df=preprocessed_old_amendments_df,
        preprocessed_new_amendments_df=preprocessed_new_amendments_df,
        original_new_amendments_df=original_new_amendments_df,
        clustering_similarity_thresholds=clustering_similarity_thresholds,
        fuzzy_match_similarity_thresholds=fuzzy_match_similarity_thresholds,
        similarity_threshold_overrides=similarity_threshold_overrides,
        column_filtering_funcs=column_filtering_funcs,
        column_group_by_columns={},
        columns_to_copy_config=columns_to_copy_config,
    )

    assert (
        result_df.loc[0, "Commentaires"]
        == textwrap.dedent("""
        Copie de Réponse, Sort depuis : PLFSS 2024
        Numéro d'amendement : 1
        Lecture : A
        Organe : Organe 1
        Colonne similaire : Corps amdt
        """).strip()
    )
    assert result_df.loc[1, "Commentaires"] == ""

    assert result_df.loc[0, "Réponse"] == "Response 1"
    assert result_df.loc[1, "Réponse"] == ""

    assert result_df.loc[0, "Sort"] == ""
    assert result_df.loc[1, "Sort"] == ""
