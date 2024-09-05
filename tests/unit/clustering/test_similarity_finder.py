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
    similar_doc_indices = similarity_finder.prefilter_similar_docs()
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
            "Year": [3000, 2021, 2021, 2021],
            "Num amdt": [1, 2, 3, 4],
            "Lecture": [1, 2, 3, 4],
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
            "Year": [2023, 2023, 2023, 2023],
            "Num amdt": [5, 6, 7, 8],
            "Lecture": [5, 6, 7, 8],
            "amdt_idx": [5, 6, 7, 8],
        }
    )
    similarity_finder = SimilarityFinder(
        old_amendments_df=old_amendments_df,
        new_amendments_df=new_amendments_df,
        default_threshold_ratio=0.7,
    )
    similarity_finder.prefilter_similar_docs()
    closest_docs = similarity_finder.find_best_matches(
        column_used_for_similarity="Exposé amdt"
    )
    assert closest_docs == {
        6: {
            "best_matching_comparison_value": -3000,
            "best_matching_doc_length": 38,
            "similarity_ratio": 1.0,
            "best_matching_doc_amdt_idx": 1,
            "column_used_for_comparison": "Exposé amdt",
        },
        8: {
            "best_matching_comparison_value": -3000,
            "best_matching_doc_amdt_idx": 1,
            "similarity_ratio": 0.7368421052631579,
            "best_matching_doc_length": 38,
            "column_used_for_comparison": "Exposé amdt",
        },
    }


def test_find_best_matches_missing_df():
    similarity_finder = SimilarityFinder(None, None)
    with pytest.raises(TypeError):
        similarity_finder.find_best_matches()


def test_find_best_matching_docs():
    new_amdt_data = {
        "text": {
            97: "Cet amendement aborde le ABC",
            98: "Cet amendement aborde le DEF",
        }
    }
    old_amdt_data = {
        "text": {
            1: "Cet amendement aborde le ABC",
            2: "Cet amendement aborde le DEF",
            3: "Cet amendement aborde le GHIJKLM",  # Between 0.75 and 0.9 similarity with amdt 1
        },
        "comparison_value": {1: -2021, 2: -2022, 3: -2023},
    }
    default_threshold_ratio = 0.75
    threshold_ratio_mappings = {"Cet amendement aborde le": 0.9}
    similar_doc_indices = {97: [1, 2], 98: [3]}

    expected_output = {
        97: {
            "best_matching_comparison_value": -2021,
            "best_matching_doc_amdt_idx": 1,
            "best_matching_doc_length": 28,
            "similarity_ratio": 1.0,
        },
    }

    closest_docs = SimilarityFinder.find_best_matching_docs(
        similar_doc_indices=similar_doc_indices,
        new_amdt_data=new_amdt_data,
        old_amdt_data=old_amdt_data,
        default_threshold_ratio=default_threshold_ratio,
        threshold_ratio_mappings=threshold_ratio_mappings,
    )

    assert closest_docs == expected_output
