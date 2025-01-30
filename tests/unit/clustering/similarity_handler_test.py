import textwrap

import pandas as pd
import pytest

from graal.clustering.similarity_handler import SimilarityHandler


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
    result_df = SimilarityHandler.copy_matches_to_amendments_df(
        target_df=target_df,
        old_amendments_df=old_amendments_df,
        closest_amdts=closest_amdts,
    )

    assert result_df.loc[0, "Réponse"] == "Response 1"
    assert (
        result_df.loc[0, "Commentaires"]
        == textwrap.dedent("""
        Réponse copiée de : PLFSS 2022
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
        Réponse copiée de : PLACSS 2023
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
        Réponse copiée de : PLFSS 2023
        Numéro d'amendement : 3
        Lecture : C
        Organe : Organe 3
        Colonne similaire : Exposé amdt
        """).strip()
    )
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
            "Organe": ["Organe 1", "Organe 2", "Organe 3"],
            "Réponse": ["Response 1", "Response 2", "Response 3"],
            "Sort": ["Sort 1", "Irrecevable 123", "Sort 3"],
            "Exposé amdt": ["Exposé 1", "Exposé 2", "Exposé 3"],
            "Corps amdt": ["Corps 1", "Corps 2", "Corps 3"],
            "timestamp": [0, 0, 0],
            "origin_project": ["PLFSS 2024", "PLACSS 2020", "PLFSS 1988"],
        }
    )

    clustering_similarity_thresholds = {
        "Exposé amdt": 1,
        "Corps amdt": 1,
    }
    fuzzy_match_similarity_thresholds = {
        "Exposé amdt": 1,
        "Corps amdt": 1,
    }
    similarity_threshold_overrides = {}

    result_df = SimilarityHandler.populate(
        preprocessed_old_amendments_df=preprocessed_old_amendments_df,
        preprocessed_new_amendments_df=preprocessed_new_amendments_df,
        original_new_amendments_df=original_new_amendments_df,
        clustering_similarity_thresholds=clustering_similarity_thresholds,
        fuzzy_match_similarity_thresholds=fuzzy_match_similarity_thresholds,
        similarity_threshold_overrides=similarity_threshold_overrides,
        column_group_by_columns={},
    )

    assert (
        result_df.loc[0, "Commentaires"]
        == textwrap.dedent("""
        Réponse copiée de : PLFSS 2024
        Numéro d'amendement : 1
        Lecture : A
        Organe : Organe 1
        Colonne similaire : Exposé amdt
        """).strip()
    )
    assert (
        result_df.loc[1, "Commentaires"]
        == textwrap.dedent("""
        Réponse copiée de : PLACSS 2020
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
        Réponse copiée de : PLFSS 1988
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

    clustering_similarity_thresholds = {
        "Corps amdt": 1,
    }
    fuzzy_match_similarity_thresholds = {
        "Corps amdt": 1,
    }
    similarity_threshold_overrides = {}

    column_filtering_funcs = {
        "Corps amdt": SimilarityHandler.filter_old_amendments_by_project,
    }

    result_df = SimilarityHandler.populate(
        preprocessed_old_amendments_df=preprocessed_old_amendments_df,
        preprocessed_new_amendments_df=preprocessed_new_amendments_df,
        original_new_amendments_df=original_new_amendments_df,
        clustering_similarity_thresholds=clustering_similarity_thresholds,
        fuzzy_match_similarity_thresholds=fuzzy_match_similarity_thresholds,
        similarity_threshold_overrides=similarity_threshold_overrides,
        column_filtering_funcs=column_filtering_funcs,
        column_group_by_columns={},
    )

    assert (
        result_df.loc[0, "Commentaires"]
        == textwrap.dedent("""
        Réponse copiée de : PLFSS 2024
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
