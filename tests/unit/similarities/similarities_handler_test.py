from unittest.mock import patch

import pandas as pd
import pytest

from graal.clustering.clustering_service import ClusteringService
from graal.similarities.similarities_handler import SimilaritiesHandler


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


def test_update_comments_with_similarities(sample_df):
    """Test the update_comments_with_similarities method."""
    similarity_percentages = {
        1: {2: 90.0},
        2: {1: 90.0},
        3: {4: 80.0},
        4: {3: 80.0},
    }

    result_df = SimilaritiesHandler.update_comments_with_similarities(
        amendments_df=sample_df,
        similarity_percentages=similarity_percentages,
    )

    assert "Amdt similaires : 102 (90%)" in result_df.loc[0, "Commentaires"]
    assert "Amdt similaires : 101 (90%)" in result_df.loc[1, "Commentaires"]
    assert "Amdt similaires : 104 (80%)" in result_df.loc[2, "Commentaires"]
    assert "Amdt similaires : 103 (80%)" in result_df.loc[3, "Commentaires"]
    assert result_df.loc[4, "Commentaires"] == ""


@patch.object(ClusteringService, "preprocess_amendments")
@patch.object(ClusteringService, "get_clusters")
@patch.object(SimilaritiesHandler, "update_comments_with_similarities")
def test_process_similarities(
    mock_update,
    mock_get_clusters,
    mock_preprocess,
    sample_df,
):
    """Test the process_similarities method."""
    clusters = {
        ("Article 1",): [[1, 2]],
        ("Article 2",): [[3, 4]],
        ("Article 3",): [[5]],
    }
    similarity_percentages = {1: {2: 90.0}, 2: {1: 90.0}}

    mock_preprocess.return_value = sample_df
    mock_get_clusters.return_value = (clusters, similarity_percentages)
    mock_update.return_value = sample_df

    # Call the method
    result_df = SimilaritiesHandler.process_similarities(
        amendments_df=sample_df,
        similarities_column="Corps amdt",
        similarity_threshold=0.8,
        group_by_columns=["Num article"],
        eps=0.4,
    )

    # Verify the mocks were called with the right arguments
    mock_preprocess.assert_called_once_with(
        amendments_df=sample_df,
        columns_to_filter=["Corps amdt"],
        columns_to_normalize=["Corps amdt"],
    )
    mock_get_clusters.assert_called_once_with(
        normalized_amdt_df=sample_df,
        group_by_columns=["Num article"],
        eps=0.4,
        refinement_pct_threshold=0.8,
    )
    mock_update.assert_called_once_with(
        amendments_df=sample_df,
        similarity_percentages=similarity_percentages,
    )

    # Verify the result
    assert result_df is mock_update.return_value
