from unittest.mock import patch

import pandas as pd
import pytest

from graal.custom_types import SimilarAmendment
from graal.similarities.similarity_search_handler import SimilaritySearchHandler


@pytest.fixture
def sample_df():
    """Create a sample dataframe for testing."""
    return pd.DataFrame(
        {
            "amdt_idx": [1, 2, 3, 4, 5],
            "Num amdt": [101, 102, 103, 104, 105],
            "Num article": [
                "Article 1",
                "Article 1",
                "Article 2",
                "Article 2",
                "Article 3",
            ],
            "Corps amdt": [
                "This is amendment body 1",
                "This is very similar to amendment body 1",
                "This is amendment body 3",
                "This is amendment body 4",
                "This is amendment body 5",
            ],
            "Commentaires": ["", "", "", "", ""],
        }
    )


def test_format_similarity_comment():
    """Test formatting similarity comments."""
    similar_amendments: list[SimilarAmendment] = [
        {"amdt_num": 101, "similarity_percentage": 85.5},
        {"amdt_num": 102, "similarity_percentage": 92.0},
    ]

    result = SimilaritySearchHandler.format_similarity_comment(similar_amendments)
    expected = "Amdt similaires : 101 (86%), 102 (92%)"

    assert result == expected


@patch("graal.clustering.clustering_service.ClusteringService.preprocess_amendments")
@patch("graal.clustering.clustering_service.ClusteringService.get_clusters")
def test_find_similar_amendments(mock_get_clusters, mock_preprocess, sample_df):
    """Test finding similar amendments."""
    # Setup mock for preprocess_amendments
    normalized_df = sample_df.copy()
    mock_preprocess.return_value = normalized_df

    # Setup mock for get_clusters
    # The similarity_percentages dict maps amendment indices to dicts of similar amendments with percentages
    similarity_percentages = {
        1: {2: 85.0},  # Amendment 1 is similar to amendment 2 with 85% similarity
        2: {1: 85.0},  # Amendment 2 is similar to amendment 1 with 85% similarity
        3: {},  # Amendment 3 has no similar amendments
        4: {},  # Amendment 4 has no similar amendments
        5: {},  # Amendment 5 has no similar amendments
    }
    mock_get_clusters.return_value = (None, similarity_percentages)

    # Call the function
    result = SimilaritySearchHandler.find_similar_amendments(
        amendments_df=sample_df,
        similarities_column="Corps amdt",
        pct_similarity_threshold=0.8,
        group_by_columns=["Num article"],
        eps=0.4,
    )

    # Verify the results
    assert len(result) == 2  # Only amendments 1 and 2 have similar amendments

    # Check amendment 1's similar amendments
    assert 1 in result
    assert len(result[1]) == 1
    assert result[1][0]["amdt_num"] == 102
    assert result[1][0]["similarity_percentage"] == pytest.approx(85.0)

    # Check amendment 2's similar amendments
    assert 2 in result
    assert len(result[2]) == 1
    assert result[2][0]["amdt_num"] == 101
    assert result[2][0]["similarity_percentage"] == pytest.approx(85.0)

    # Verify the mocks were called with the correct arguments
    mock_preprocess.assert_called_once_with(
        amendments_df=sample_df,
        columns_to_filter=["Corps amdt"],
        columns_to_normalize=["Corps amdt"],
    )

    mock_get_clusters.assert_called_once_with(
        normalized_amdt_df=normalized_df,
        group_by_columns=["Num article"],
        text_column="Corps amdt",
        eps=0.4,
        refinement_pct_threshold=0.8,
    )


@patch("graal.clustering.clustering_service.ClusteringService.preprocess_amendments")
@patch("graal.clustering.clustering_service.ClusteringService.get_clusters")
def test_find_similar_amendments_with_default_group_by(
    mock_get_clusters, mock_preprocess, sample_df
):
    """Test finding similar amendments with default group_by_columns."""
    # Setup mocks
    normalized_df = sample_df.copy()
    mock_preprocess.return_value = normalized_df
    mock_get_clusters.return_value = (None, {})

    # Call the function without specifying group_by_columns
    SimilaritySearchHandler.find_similar_amendments(
        amendments_df=sample_df, similarities_column="Corps amdt"
    )

    # Verify the default group_by_columns was used
    mock_get_clusters.assert_called_once_with(
        normalized_amdt_df=normalized_df,
        group_by_columns=["Num article"],  # Default value
        text_column="Corps amdt",
        eps=0.4,
        refinement_pct_threshold=0.8,
    )


@patch("graal.clustering.clustering_service.ClusteringService.preprocess_amendments")
@patch("graal.clustering.clustering_service.ClusteringService.get_clusters")
def test_find_similar_amendments_empty_result(
    mock_get_clusters, mock_preprocess, sample_df
):
    """Test finding similar amendments with no similarities found."""
    # Setup mocks
    normalized_df = sample_df.copy()
    mock_preprocess.return_value = normalized_df
    mock_get_clusters.return_value = (None, {})  # No similarities

    # Call the function
    result = SimilaritySearchHandler.find_similar_amendments(
        amendments_df=sample_df, similarities_column="Corps amdt"
    )

    # Verify the result is an empty dictionary
    assert result == {}
