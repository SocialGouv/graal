import pandas as pd

from graal.utils.build_similarity_db import (
    remove_oldest_and_without_response,
)


def test_remove_oldest_and_without_response():
    # Create a sample DataFrame
    data = {
        "amdt_idx": [1, 2, 3, 4, 5],
        "timestamp": [2020, 2021, 2019, 2021, 2020],
        "Réponse": [
            "Short",
            "Medium length",
            "Longest response",
            "Another long one",
            "Brief",
        ],
    }
    df = pd.DataFrame(data)

    # Create a cluster of indices to filter
    cluster = [1, 2, 3, 4, 5]

    # Call the function
    result = remove_oldest_and_without_response(df, cluster)

    # Expected result after sorting and removing the first element
    expected = [1, 2, 3, 5]

    # Assert that the result matches the expected output
    assert sorted(result) == expected, f"Expected {expected}, but got {result}"

    # Test with an empty cluster
    empty_result = remove_oldest_and_without_response(df, [])
    assert empty_result == [], "Expected an empty list for an empty cluster"

    # Test with a single-element cluster
    single_result = remove_oldest_and_without_response(df, [3])
    assert single_result == [], "Expected an empty list for a single-element cluster"
