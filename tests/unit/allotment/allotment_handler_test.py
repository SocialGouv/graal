import pandas as pd

from graal.allotment.allotment_handler import AllotmentHandler


def test_filter_amdts_to_keep_one_per_allotment():
    # Sample input dataframe
    normalized_amdt_df = pd.DataFrame(
        {
            "amdt_idx": [1, 2, 3, 4, 5, 6, 7],
            "other_column": ["a", "b", "c", "d", "e", "f", "g"],
        }
    )

    # Sample allotment clusters
    allotted_amdt_clusters: dict[tuple, list[list[int]]] = {
        ("Lecture1",): [[1, 2, 3], [4, 5]],
        ("Lecture2",): [[6, 7]],
    }

    # Expected output: only the first amendment in each cluster should remain
    expected_filtered_df = pd.DataFrame(
        {"amdt_idx": [1, 4, 6], "other_column": ["a", "d", "f"]}
    )

    # Call the function
    result_df = AllotmentHandler.filter_amdts_to_keep_one_per_allotment(
        normalized_amdt_df, allotted_amdt_clusters
    )

    # Reset index for comparison
    result_df = result_df.reset_index(drop=True)
    expected_filtered_df = expected_filtered_df.reset_index(drop=True)

    # Assert the filtered dataframe matches the expected output
    pd.testing.assert_frame_equal(result_df, expected_filtered_df)


def test_populate():
    # Input: original_amendments_df
    original_amendments_df = pd.DataFrame(
        {
            "amdt_idx": [1, 2, 3, 4, 5, 6, 7],
            "Num amdt": [101, 102, 103, 201, 202, 203, 301],
            "Allotissement": [None, None, None, None, None, None, None],
            "Lecture": [
                "Lecture1",
                "Lecture1",
                "Lecture1",
                "Lecture2",
                "Lecture2",
                "Lecture2",
                "Lecture2",
            ],
        }
    )

    # Input: pipeline_result_amdt_df
    pipeline_result_amdt_df = pd.DataFrame(
        {
            "amdt_idx": [1, 2, 3, 4, 5, 6, 7],
            "column_to_copy": ["A", "B", "C", "D", "E", "F", "G"],
            "Lecture": [
                "Lecture1",
                "Lecture1",
                "Lecture1",
                "Lecture2",
                "Lecture2",
                "Lecture2",
                "Lecture2",
            ],
        }
    )

    # Sample clusters dict
    allotted_amdt_clusters: dict[tuple, list[list[int]]] = {
        ("Lecture1",): [[1, 2, 3]],
        ("Lecture2",): [[4, 5, 6]],
    }

    # Columns to copy
    columns_to_copy = ["column_to_copy"]

    # Expected result: original_amendments_df after populating Allotissement and copying columns
    expected_df = pd.DataFrame(
        {
            "amdt_idx": [1, 2, 3, 4, 5, 6, 7],
            "Num amdt": [101, 102, 103, 201, 202, 203, 301],
            "Allotissement": [
                "101,102,103",
                "101,102,103",
                "101,102,103",
                "201,202,203",
                "201,202,203",
                "201,202,203",
                None,
            ],
            "Lecture": [
                "Lecture1",
                "Lecture1",
                "Lecture1",
                "Lecture2",
                "Lecture2",
                "Lecture2",
                "Lecture2",
            ],
            "column_to_copy": ["A", "A", "A", "D", "D", "D", "G"],
        }
    )

    # Call the function
    result_df = AllotmentHandler.populate(
        original_amendments_df,
        pipeline_result_amdt_df,
        allotted_amdt_clusters,
        columns_to_copy,
    )

    # Reset index for comparison
    result_df = result_df.reset_index(drop=True)
    expected_df = expected_df.reset_index(drop=True)

    # Assert that the resulting dataframe matches the expected dataframe
    pd.testing.assert_frame_equal(result_df, expected_df)
