from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from graal.clustering.clustering_service import ClusteringService
from graal.utils.amendment_pre_processor import AmendmentPreProcessor


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
        }
    )


@patch.object(AmendmentPreProcessor, "drop_empty_rows_in_columns")
@patch.object(AmendmentPreProcessor, "handle_common_amendment_bodies")
@patch.object(AmendmentPreProcessor, "normalize_amendments")
def test_preprocess_amendments(
    mock_normalize, mock_handle_common, mock_drop_empty, sample_df
):
    """Test the preprocess_amendments method."""
    mock_drop_empty.return_value = sample_df.copy()
    mock_handle_common.return_value = sample_df.copy()
    mock_normalize.return_value = sample_df.copy()

    result = ClusteringService.preprocess_amendments(
        amendments_df=sample_df,
        columns_to_filter=["Corps amdt"],
        columns_to_normalize=["Corps amdt"],
    )

    call_args = mock_drop_empty.call_args[1]
    assert_frame_equal(call_args["amendments_df"], sample_df)
    assert call_args["columns_to_filter"] == ["Corps amdt"]
    mock_handle_common.assert_called_once_with(
        amendments_df=mock_drop_empty.return_value
    )
    mock_normalize.assert_called_once_with(
        amendments_df=mock_handle_common.return_value,
        columns_to_normalize=["Corps amdt"],
    )

    assert_frame_equal(result, mock_normalize.return_value)


def test_create_tfidf_clusters(sample_df):
    """Test the create_tfidf_clusters method."""
    mock_cluster_finder = MagicMock()
    mock_cluster_finder.find_similarity_clusters.return_value = {
        "key": [[1, 2], [3, 4]]
    }

    with patch(
        "graal.clustering.clustering_service.AmendmentsClusterFinder",
        return_value=mock_cluster_finder,
    ) as mock_constructor:
        cluster_finder, clusters = ClusteringService.create_tfidf_clusters(
            normalized_amdt_df=sample_df,
            group_by_columns=["Num article"],
            eps=0.4,
        )

        mock_constructor.assert_called_once_with(
            amendments_df=sample_df, group_by_columns=["Num article"]
        )

        mock_cluster_finder.find_similarity_clusters.assert_called_once_with(eps=0.4)

        assert cluster_finder == mock_cluster_finder
        assert clusters == {"key": [[1, 2], [3, 4]]}


def test_apply_levenshtein_refinement_with_similarity_threshold():
    """Test the apply_levenshtein_refinement method with a similarity threshold."""
    mock_cluster_finder = MagicMock()
    mock_cluster_finder.refine_clusters_with_distance.return_value = {
        "key": [[1, 2], [3, 4]]
    }

    result = ClusteringService.apply_levenshtein_refinement(
        cluster_finder=mock_cluster_finder,
        threshold=0.8,
        is_similarity_threshold=True,
    )

    # Verify the mock was called with the right arguments (1.0 - 0.8 = 0.2)
    args, kwargs = mock_cluster_finder.refine_clusters_with_distance.call_args
    assert kwargs["threshold"] == pytest.approx(0.2)

    assert result == {"key": [[1, 2], [3, 4]]}


def test_apply_levenshtein_refinement_with_distance_threshold():
    """Test the apply_levenshtein_refinement method with a distance threshold."""
    mock_cluster_finder = MagicMock()
    mock_cluster_finder.refine_clusters_with_distance.return_value = {
        "key": [[1, 2], [3, 4]]
    }

    result = ClusteringService.apply_levenshtein_refinement(
        cluster_finder=mock_cluster_finder,
        threshold=0.0001,
        is_similarity_threshold=False,
    )

    args, kwargs = mock_cluster_finder.refine_clusters_with_distance.call_args
    assert kwargs["threshold"] == pytest.approx(0.0001)

    # Verify the result
    assert result == {"key": [[1, 2], [3, 4]]}


@patch.object(ClusteringService, "create_tfidf_clusters")
@patch.object(ClusteringService, "apply_levenshtein_refinement")
def test_get_clusters(mock_apply_refinement, mock_create_clusters, sample_df):
    """Test the get_clusters method."""
    mock_cluster_finder = MagicMock()
    mock_create_clusters.return_value = (
        mock_cluster_finder,
        {"key": [[1, 2], [3, 4]]},
    )
    mock_apply_refinement.return_value = {"key": [[1, 2, 3], [4, 5]]}

    result = ClusteringService.get_clusters(
        normalized_amdt_df=sample_df,
        group_by_columns=["Num article"],
        eps=0.4,
        threshold=0.8,
        is_similarity_threshold=True,
    )

    mock_create_clusters.assert_called_once_with(
        normalized_amdt_df=sample_df, group_by_columns=["Num article"], eps=0.4
    )
    mock_apply_refinement.assert_called_once_with(
        cluster_finder=mock_cluster_finder,
        threshold=0.8,
        is_similarity_threshold=True,
    )

    assert result == {"key": [[1, 2, 3], [4, 5]]}
