from unittest.mock import patch

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
    with patch(
        "graal.clustering.clustering_service.AmendmentsClusterFinder.find_similarity_clusters",
        return_value={"key": [[1, 2], [3, 4]]},
    ) as mock_find_clusters:
        clusters = ClusteringService.create_tfidf_clusters(
            normalized_amdt_df=sample_df,
            group_by_columns=["Num article"],
            text_column="Corps amdt",
            eps=0.4,
        )

        mock_find_clusters.assert_called_once_with(
            amendments_df=sample_df,
            group_by_columns=["Num article"],
            text_column="Corps amdt",
            eps=0.4,
        )

        assert clusters == {"key": [[1, 2], [3, 4]]}


def test_apply_levenshtein_refinement_with_similarity_threshold(sample_df):
    """Test the apply_levenshtein_refinement method with a similarity threshold."""
    tfidf_clusters = {("Article 1",): [[1, 2], [3, 4]]}

    with patch(
        "graal.clustering.clustering_service.AmendmentsClusterFinder.refine_clusters_with_distance",
        return_value=(
            {("Article 1",): [[1, 2], [3, 4]]},
            {1: {2: 90.0}, 2: {1: 90.0}, 3: {4: 85.0}, 4: {3: 85.0}},
        ),
    ) as mock_refine:
        clusters, similarity_percentages = (
            ClusteringService.apply_levenshtein_refinement(
                amendments_df=sample_df,
                group_by_columns=["Num article"],
                text_column="Corps amdt",
                tfidf_clusters=tfidf_clusters,
                pct_threshold=0.8,
            )
        )

        # Verify the mock was called with the right arguments (1.0 - 0.8 = 0.2)
        mock_refine.assert_called_once_with(
            amendments_df=sample_df,
            group_by_columns=["Num article"],
            text_column="Corps amdt",
            tfidf_clusters=tfidf_clusters,
            distance_threshold=pytest.approx(0.2),
        )

        assert clusters == {("Article 1",): [[1, 2], [3, 4]]}
        assert similarity_percentages == {
            1: {2: 90.0},
            2: {1: 90.0},
            3: {4: 85.0},
            4: {3: 85.0},
        }


def test_apply_levenshtein_refinement_with_distance_threshold(sample_df):
    """Test the apply_levenshtein_refinement method with a distance threshold."""
    tfidf_clusters = {("Article 1",): [[1, 2]], ("Article 2",): [[3, 4]]}

    clusters, similarity_percentages = ClusteringService.apply_levenshtein_refinement(
        amendments_df=sample_df,
        group_by_columns=["Num article"],
        text_column="Corps amdt",
        tfidf_clusters=tfidf_clusters,
        pct_threshold=0.6,
    )

    assert clusters == {
        ("Article 1",): [[1, 2]],
        ("Article 2",): [[3, 4]],
        ("Article 3",): [],
    }
    # Check similarity percentages are as expected (around 60% for 1/2, around 96% for 3/4)
    assert similarity_percentages[1][2] == pytest.approx(60.0, abs=0.1)
    assert similarity_percentages[2][1] == pytest.approx(60.0, abs=0.1)
    assert similarity_percentages[3][4] == pytest.approx(95.83, abs=0.1)
    assert similarity_percentages[4][3] == pytest.approx(95.83, abs=0.1)


@patch.object(ClusteringService, "create_tfidf_clusters")
@patch.object(ClusteringService, "apply_levenshtein_refinement")
def test_get_clusters(mock_apply_refinement, mock_create_clusters, sample_df):
    """Test the get_clusters method."""
    tfidf_clusters = {("Article 1",): [[1, 2], [3, 4]]}
    mock_create_clusters.return_value = tfidf_clusters
    mock_apply_refinement.return_value = (
        {("Article 1",): [[1, 2, 3], [4, 5]]},
        {
            1: {2: 90.0, 3: 85.0},
            2: {1: 90.0, 3: 80.0},
            3: {1: 85.0, 2: 80.0},
            4: {5: 95.0},
            5: {4: 95.0},
        },
    )

    clusters, similarity_percentages = ClusteringService.get_clusters(
        normalized_amdt_df=sample_df,
        group_by_columns=["Num article"],
        text_column="Corps amdt",
        eps=0.4,
        refinement_pct_threshold=0.8,
    )

    mock_create_clusters.assert_called_once_with(
        normalized_amdt_df=sample_df,
        group_by_columns=["Num article"],
        text_column="Corps amdt",
        eps=0.4,
    )
    mock_apply_refinement.assert_called_once_with(
        amendments_df=sample_df,
        group_by_columns=["Num article"],
        text_column="Corps amdt",
        tfidf_clusters=tfidf_clusters,
        pct_threshold=0.8,
    )

    assert clusters == {("Article 1",): [[1, 2, 3], [4, 5]]}
    assert similarity_percentages == {
        1: {2: 90.0, 3: 85.0},
        2: {1: 90.0, 3: 80.0},
        3: {1: 85.0, 2: 80.0},
        4: {5: 95.0},
        5: {4: 95.0},
    }
