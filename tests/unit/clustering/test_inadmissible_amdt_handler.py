from unittest.mock import MagicMock, patch

import pandas as pd

from amendements_intelligents.clustering.inadmissible_amdt_handler import (
    InadmissibleAmendmentHandler,
)


@patch("amendements_intelligents.clustering.inadmissible_amdt_handler.pd.read_pickle")
@patch("amendements_intelligents.clustering.inadmissible_amdt_handler.SimilarityFinder")
def test_process(mock_similarity_finder, mock_read_pickle):
    test_cases = [
        {
            "name": "no_comments",
            "input_comments": [None, None],
            "expected_comments": [
                "Attention : Irrecevable en commission",
                "Attention : Irrecevable en commission",
            ],
        },
        {
            "name": "empty_comments",
            "input_comments": ["", ""],
            "expected_comments": [
                "Attention : Irrecevable en commission",
                "Attention : Irrecevable en commission",
            ],
        },
        {
            "name": "existing_comments",
            "input_comments": ["Existing comment 1", "Existing comment 2"],
            "expected_comments": [
                "Attention : Irrecevable en commission\n\nExisting comment 1",
                "Attention : Irrecevable en commission\n\nExisting comment 2",
            ],
        },
        {
            "name": "missing_comments_column",
            "input_comments": None,
            "expected_comments": [
                "Attention : Irrecevable en commission",
                "Attention : Irrecevable en commission",
            ],
        },
    ]

    sample_filtered_amendments_df = pd.DataFrame(
        {
            "amdt_idx": [1, 2],
            "Exposé amdt": ["text1", "text2"],
            "Sort": ["Irrecevable", "Recevable"],
        }
    )

    mock_read_pickle.return_value = sample_filtered_amendments_df

    mock_similarity_instance = MagicMock()
    mock_similarity_instance.find_best_matches.return_value = {
        1: {"best_matching_doc_amdt_idx": 1},
        2: {"best_matching_doc_amdt_idx": 2},
    }
    mock_similarity_finder.return_value = mock_similarity_instance

    handler = InadmissibleAmendmentHandler(preprocessed_inadmissible_file="dummy_path")

    for case in test_cases:
        sample_amendments_df = pd.DataFrame(
            {
                "amdt_idx": [1, 2],
                "Exposé amdt": ["text1", "text2"],
                "Commentaires": case["input_comments"],
            }
        )

        result_df = handler.process(sample_amendments_df)

        assert (
            result_df.loc[result_df["amdt_idx"] == 1, "Sort"].values[0] == "Irrecevable"
        )
        assert (
            result_df.loc[result_df["amdt_idx"] == 2, "Sort"].values[0] == "Recevable"
        )
        assert (
            result_df.loc[result_df["amdt_idx"] == 1, "Commentaires"].values[0]
            == case["expected_comments"][0]
        )
        assert (
            result_df.loc[result_df["amdt_idx"] == 2, "Commentaires"].values[0]
            == case["expected_comments"][1]
        )
