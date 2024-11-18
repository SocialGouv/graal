import textwrap

import pandas as pd
import pytest

from graal.utils.amendment_copier import AmendmentCopier


@pytest.fixture
def sample_data():
    new_amendments_df = pd.DataFrame(
        {
            "Num amdt": [1, 2, 3],
            "Lecture": ["A", "B", "C"],
            "amdt_idx": [97, 98, 99],
        }
    )
    old_amendments_df = pd.DataFrame(
        {
            "Num amdt": [1, 2, 3],
            "amdt_idx": [1, 2, 3],
            "Lecture": ["A", "B", "C"],
            "Objet amdt": ["Objet 1", "Objet 2", "Objet 3"],
            "Organe": ["Organe 1", "Organe 2", "Organe 3"],
            "Réponse": ["Response 1", "Response 2", "Response 3"],
            "Corps amdt orig": ["Corps 1", "Corps 2", "Corps 3"],
            "Exposé amdt orig": ["Exposé 1", "Exposé 2", "Exposé 3"],
            "Objet orig": ["Objet 1", "Objet 2", "Objet 3"],
            "Sort": ["Sort 1", "Irrecevable 123", "Sort 3"],
            "origin_project": ["PLFSS", "PLACSS", "PLFSS"],
        }
    )
    closest_docs = {
        97: {
            "best_matching_doc_amdt_idx": 1,
            "best_matching_doc_lecture": "A",
            "best_matching_comparison_value": -1640995200,  # 2022
            "column_used_for_comparison": "Exposé amdt",
        },
        98: {
            "best_matching_doc_amdt_idx": 2,
            "best_matching_doc_lecture": "B",
            "best_matching_comparison_value": -1609459200,  # 2021
            "column_used_for_comparison": "Exposé amdt",
        },
        99: {
            "best_matching_doc_amdt_idx": 3,
            "best_matching_comparison_value": -1577836800,  # 2020
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
            "Corps amdt trouvé": ["", "", ""],
            "Exposé amdt trouvé": ["", "", ""],
            "Sort": ["", "", ""],
        }
    )
    return new_amendments_df, old_amendments_df, closest_docs, target_df


def test_copy_matches_to_amendments_df(sample_data):
    new_amendments_df, old_amendments_df, closest_docs, target_df = sample_data
    copier = AmendmentCopier(new_amendments_df, old_amendments_df, closest_docs)
    result_df = copier.copy_matches_to_amendments_df(target_df)

    assert result_df.loc[0, "Réponse"] == "Response 1"
    assert (
        result_df.loc[0, "Commentaires"]
        == textwrap.dedent("""
        Réponse copiée de : PLFSS (traité en 2022)
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
        Réponse copiée de : PLACSS (traité en 2021)
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
        Réponse copiée de : PLFSS (traité en 2020)
        Numéro d'amendement : 3
        Lecture : C
        Organe : Organe 3
        Colonne similaire : Exposé amdt
        """).strip()
    )
    assert result_df.loc[2, "Sort"] == ""
