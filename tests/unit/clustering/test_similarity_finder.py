import pandas as pd
import pytest

from amendements_intelligents.clustering.similarity_finder import SimilarityFinder


@pytest.mark.parametrize(
    "old_amendments_df, new_amendments_df",
    [
        (
            pd.DataFrame(
                {
                    "Exposé amdt": [
                        "Cet amendement aborde le ABC et le DEF",
                        "Cet amendement aborde le GHI",
                        "Cet amendement aborde le JKL et le MNO",
                        "Un amendement qui n'a rien à voir",
                    ],
                }
            ),
            pd.DataFrame(
                {
                    "Exposé amdt": [
                        "Cet amendement aborde le JKL",
                        "Cet amendement aborde le ABC et le DEF",
                        "no match",
                        "Cet amendement aborde le DEF",
                    ],
                }
            ),
        )
    ],
)
def test_prefilter_similar_docs(old_amendments_df, new_amendments_df):
    similarity_finder = SimilarityFinder(old_amendments_df, new_amendments_df)
    similar_doc_indices = similarity_finder.prefilter_similar_docs()
    assert similar_doc_indices == {0: [2], 1: [0], 3: [0]}


@pytest.mark.parametrize(
    "old_amendments_df, new_amendments_df",
    [
        (
            pd.DataFrame(
                {
                    "Exposé amdt": [
                        "Cet amendement aborde le ABC et le DEF",
                        "Cet amendement aborde le GHI",
                        "Cet amendement aborde le ABC et le DEF",
                        "Un amendement qui n'a rien à voir",
                    ],
                    "Year": [3000, 2021, 2021, 2021],
                }
            ),
            pd.DataFrame(
                {
                    "Exposé amdt": [
                        "Cet amendement aborde le JKL",
                        "Cet amendement aborde le ABC et le DEF",
                        "no match",
                        "Cet amendement aborde le DEF",
                    ],
                    "Year": [2023, 2023, 2023, 2023],
                }
            ),
        )
    ],
)
def test_find_best_matches(old_amendments_df, new_amendments_df):
    similarity_finder = SimilarityFinder(
        old_amendments_df, new_amendments_df, default_threshold_ratio=0.7
    )
    similarity_finder.prefilter_similar_docs()
    closest_docs = similarity_finder.find_best_matches(
        column_used_for_comparison="Exposé amdt"
    )
    assert closest_docs == {
        1: {
            "best_matching_comparison_value": -3000,
            "best_matching_doc_idx": 0,
            "best_matching_doc_length": 38,
            "similarity_ratio": 1.0,
        },
        3: {
            "best_matching_comparison_value": -3000,
            "best_matching_doc_idx": 0,
            "best_matching_doc_length": 38,
            "similarity_ratio": 0.7368421052631579,
        },
    }


def test_find_best_matches_without_prefilter():
    similarity_finder = SimilarityFinder(None, None)
    with pytest.raises(TypeError):
        similarity_finder.find_best_matches()
