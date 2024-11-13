import pandas as pd
import pytest

from amendements_intelligents.clustering.similarity_finder import SimilarityFinder


def test_prefilter_similar_docs():
    old_amendments_df = pd.DataFrame(
        {
            "Exposé amdt": [
                "Cet amendement aborde le ABC et le DEF",
                "Cet amendement aborde le GHI",
                "Cet amendement aborde le JKL et le MNO",
                "Un amendement qui n'a rien à voir",
            ],
            "amdt_idx": [1, 2, 3, 4],
        }
    )
    new_amendments_df = pd.DataFrame(
        {
            "Exposé amdt": [
                "Cet amendement aborde le JKL",
                "Cet amendement aborde le ABC et le DEF",
                "no match",
                "Cet amendement aborde le DEF",
            ],
            "amdt_idx": [5, 6, 7, 8],
        }
    )
    similarity_finder = SimilarityFinder(old_amendments_df, new_amendments_df)
    similar_doc_indices = similarity_finder.clusterize_similar_amdts(
        clustering_similarity_threshold=0.7
    )
    assert similar_doc_indices == {5: [3], 6: [1], 8: [1]}


def test_find_best_matches():
    old_amendments_df = pd.DataFrame(
        {
            "Exposé amdt": [
                "Cet amendement aborde le ABC et le DEF",
                "Cet amendement aborde le GHI",
                "Cet amendement aborde le ABC et le DEF",
                "Un amendement qui n'a rien à voir",
            ],
            "timestamp": [3000, 1, 1, 1],
            "Num amdt": [1, 2, 3, 4],
            "Lecture": [1, 2, 3, 4],
            "amdt_idx": [1, 2, 3, 4],
            "Réponse": [
                "Response 1",
                "Response text",
                "Response 3",
                "Another response",
            ],
        }
    )
    new_amendments_df = pd.DataFrame(
        {
            "Exposé amdt": [
                "Cet amendement aborde le JKL",
                "Cet amendement aborde le ABC et le DEF",
                "no match",
                "Cet amendement aborde le DEF",
            ],
            "timestamp": [3, 3, 3, 3],
            "Num amdt": [5, 6, 7, 8],
            "Lecture": [5, 6, 7, 8],
            "amdt_idx": [5, 6, 7, 8],
        }
    )
    similarity_finder = SimilarityFinder(
        old_amendments_df=old_amendments_df,
        new_amendments_df=new_amendments_df,
    )
    clusters = similarity_finder.clusterize_similar_amdts()
    closest_docs = similarity_finder.find_best_matches(
        clusters=clusters,
        column_used_for_similarity="Exposé amdt",
        fuzzy_match_similarity_threshold=0.7,
        similarity_threshold_overrides={},
    )
    assert closest_docs == {
        6: {
            "best_matching_comparison_value": -3000,
            "similarity_ratio": 1.0,
            "best_matching_doc_amdt_idx": 1,
            "column_used_for_comparison": "Exposé amdt",
        },
        8: {
            "best_matching_comparison_value": -3000,
            "best_matching_doc_amdt_idx": 1,
            "similarity_ratio": 0.7368421052631579,
            "column_used_for_comparison": "Exposé amdt",
        },
    }


def test_find_best_matches_missing_df():
    similarity_finder = SimilarityFinder(None, None)
    with pytest.raises(TypeError):
        similarity_finder.find_best_matches(
            column_used_for_similarity="Exposé amdt",
            clusters={},
            fuzzy_match_similarity_threshold=0.7,
            similarity_threshold_overrides={},
        )


def test_find_best_matching_docs():
    old_amdt_data = {
        "text": {
            1: "Cet amendement aborde le ABC",
            2: "Cet amendement aborde le DEF",
            3: "Cet amendement aborde le GHIJKLM",  # Between 0.75 and 0.9 similarity with amdt 1
        },
        "comparison_value": {1: -1, 2: -2, 3: -3},
        "response": {1: "Response 1", 2: "Response 2", 3: "Response 3"},
    }
    new_amdt_data = {
        "text": {
            97: "Cet amendement aborde le ABC",
            98: "Cet amendement aborde le DEF",
        }
    }
    default_threshold_ratio = 0.75
    threshold_ratio_mappings = {"Cet amendement aborde le": 0.9}
    similar_doc_indices = {97: [1, 2], 98: [3]}

    expected_output = {
        97: {
            "best_matching_comparison_value": -1,
            "best_matching_doc_amdt_idx": 1,
            "similarity_ratio": 1.0,
        },
    }

    closest_docs = SimilarityFinder.find_best_matching_docs(
        clusters=similar_doc_indices,
        new_amdt_data=new_amdt_data,
        old_amdt_data=old_amdt_data,
        fuzzy_match_similarity_threshold=default_threshold_ratio,
        similarity_threshold_overrides=threshold_ratio_mappings,
    )

    assert closest_docs == expected_output


def test_find_best_matching_docs_with_preference_for_non_empty_responses():
    old_amdt_data = {
        "text": {
            1: "Cet amendement aborde le ABC",
            2: "Cet amendement aborde le DEF",
            3: "Cet amendement aborde le GHIJKLM",
            4: "Cet amendement aborde le AB",  # Slightly worse than 1 but with non-empty response
        },
        "comparison_value": {1: -1, 2: -2, 3: -3, 4: -1},
        "response": {1: "", 2: "", 3: "", 4: "Non-empty response"},
    }
    new_amdt_data = {
        "text": {
            97: "Cet amendement aborde le ABC",
            98: "Cet amendement aborde le DEF",
        }
    }
    default_threshold_ratio = 0.75
    threshold_ratio_mappings = {"Cet amendement aborde le": 0.9}
    similar_doc_indices = {97: [1, 4], 98: [2]}

    expected_output = {
        97: {
            "best_matching_comparison_value": -1,
            "best_matching_doc_amdt_idx": 4,
            "similarity_ratio": 0.9629629629629629,
        },
        98: {
            "best_matching_comparison_value": -2,
            "best_matching_doc_amdt_idx": 2,
            "similarity_ratio": 1.0,
        },
    }

    closest_docs = SimilarityFinder.find_best_matching_docs(
        clusters=similar_doc_indices,
        new_amdt_data=new_amdt_data,
        old_amdt_data=old_amdt_data,
        fuzzy_match_similarity_threshold=default_threshold_ratio,
        similarity_threshold_overrides=threshold_ratio_mappings,
    )

    assert closest_docs == expected_output
