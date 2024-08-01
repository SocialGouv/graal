import textwrap

import pandas as pd
import pytest

from amendements_intelligents.utils.plfss_amendment_copier import (
    AmendmentCopier,
)


@pytest.fixture
def sample_data():
    new_amendments_df = pd.DataFrame(
        {"Num amdt": [1, 2, 3], "Lecture": ["A", "B", "C"]}
    )
    old_amendments_df = pd.DataFrame(
        {
            "Num amdt": [1, 2, 3],
            "Lecture": ["A", "B", "C"],
            "Réponse": ["Response 1", "Response 2", "Response 3"],
            "Corps amdt orig": ["Corps 1", "Corps 2", "Corps 3"],
            "Exposé amdt orig": ["Exposé 1", "Exposé 2", "Exposé 3"],
            "Sort": ["Sort 1", "Irrecevable 123", "Sort 3"],
        }
    )
    closest_docs = {
        0: {"best_matching_doc_idx": 0, "best_matching_comparison_value": -2022},
        1: {"best_matching_doc_idx": 1, "best_matching_comparison_value": -2021},
        2: {"best_matching_doc_idx": 2, "best_matching_comparison_value": -2020},
    }
    target_df = pd.DataFrame(
        {
            "Num amdt": [1, 2, 3],
            "Lecture": ["A", "B", "C"],
            "Réponse": ["", "", ""],
            "Commentaires": ["", "", ""],
            "Corps amdt trouvé": ["", "", ""],
            "Exposé amdt trouvé": ["", "", ""],
            "Sort": ["", "", ""],
        }
    )
    return new_amendments_df, old_amendments_df, closest_docs, target_df


def test_copy_matches_to_plfss_df(sample_data):
    new_amendments_df, old_amendments_df, closest_docs, target_df = sample_data
    copier = AmendmentCopier(new_amendments_df, old_amendments_df, closest_docs)
    result_df = copier.copy_matches_to_plfss_df(target_df)

    assert result_df.loc[0, "Réponse"] == "Response 1"
    assert result_df.loc[0, "Commentaires"] == textwrap.dedent("""
        Réponse copiée du PLFSS 2022
        Lecture : A
        Numéro d'amendement : 1
        """)
    assert result_df.loc[0, "Corps amdt found"] == "Corps 1"
    assert result_df.loc[0, "Exposé amdt found"] == "Exposé 1"
    assert result_df.loc[0, "Sort"] == ""

    assert result_df.loc[1, "Réponse"] == "Response 2"
    assert result_df.loc[1, "Commentaires"] == textwrap.dedent("""
        Réponse copiée du PLFSS 2021
        Lecture : B
        Numéro d'amendement : 2
        """)
    assert result_df.loc[1, "Corps amdt found"] == "Corps 2"
    assert result_df.loc[1, "Exposé amdt found"] == "Exposé 2"
    assert result_df.loc[1, "Sort"] == "Irrecevable 123"

    assert result_df.loc[2, "Réponse"] == "Response 3"
    assert result_df.loc[2, "Commentaires"] == textwrap.dedent("""
        Réponse copiée du PLFSS 2020
        Lecture : C
        Numéro d'amendement : 3
        """)
    assert result_df.loc[2, "Corps amdt found"] == "Corps 3"
    assert result_df.loc[2, "Exposé amdt found"] == "Exposé 3"
    assert result_df.loc[2, "Sort"] == ""
