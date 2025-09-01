import logging
import logging.config

import pandas as pd
import pytest

from graal.clustering.cluster_finder import AmendmentsClusterFinder

logging.config.fileConfig("logging.conf")


@pytest.fixture
def df():
    data = {
        "Lecture": ["A", "A", "B", "B", "B", "C", "C", "C", "C"],
        "amdt_idx": [0, 1, 2, 3, 4, 5, 6, 7, 8],
        "Corps amdt": [
            "text foo in lecture A",
            "some text that is not similar to the first one in order to make some tests fail for lecture A",
            "text foo in lecture B",
            "text bar in lecture B",
            "text bar in lecture B",
            "text foo in lecture C",
            "text foo in lecture C",
            "text bar in lecture C",
            "text bar in lecture C",
        ],
    }
    return pd.DataFrame(data)


@pytest.mark.parametrize(
    "lecture_group, eps, expected_amdt_idx_clusters",
    [
        ("A", 1, [[0, 1]]),
        ("A", 0.5, []),
        ("B", 0.5, [[2, 3, 4]]),
        ("C", 0.5, [[5, 6, 7, 8]]),
        ("A", 0.2, []),
        ("B", 0.2, [[3, 4]]),
        ("C", 0.2, [[5, 6], [7, 8]]),
    ],
)
def test_find_similarity_clusters(df, lecture_group, eps, expected_amdt_idx_clusters):
    tfidf_clusters_per_lecture = AmendmentsClusterFinder.find_similarity_clusters(
        amendments_df=df,
        group_by_columns=["Lecture"],
        text_column="Corps amdt",
        eps=eps,
    )
    assert tfidf_clusters_per_lecture[(lecture_group,)] == expected_amdt_idx_clusters


@pytest.mark.parametrize(
    "lecture_group, eps, expected_amdt_idx_clusters",
    [
        ("A", 1, [[1, 2]]),
        ("A", 0.5, []),
        ("B", 0.5, [[3, 4, 8]]),
        ("C", 0.5, [[0, 5, 6, 9]]),
        ("A", 0.2, []),
        ("B", 0.2, [[4, 8]]),
        ("C", 0.2, [[0, 5], [6, 9]]),
    ],
)
def test_find_similarity_clusters_messy_data(
    lecture_group, eps, expected_amdt_idx_clusters
):
    data = {
        "Lecture": ["C", "A", "A", "B", "B", "C", "C", "B", "B", "C"],
        "amdt_idx": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
        "Corps amdt": [
            "text foo in lecture C",
            "text foo in lecture A",
            "some text that is not similar to the first one in order to make some tests fail for lecture A",
            "text foo in lecture B",
            "text bar in lecture B",
            "text foo in lecture C",
            "text bar in lecture C",
            "",
            "text bar in lecture B",
            "text bar in lecture C",
        ],
    }
    df = pd.DataFrame(data)
    tfidf_clusters_per_lecture = AmendmentsClusterFinder.find_similarity_clusters(
        amendments_df=df,
        group_by_columns=["Lecture"],
        text_column="Corps amdt",
        eps=eps,
    )
    assert tfidf_clusters_per_lecture[(lecture_group,)] == expected_amdt_idx_clusters


@pytest.mark.parametrize(
    "lecture_group, distance_threshold, expected_amdt_idx_clusters",
    [
        ("A", 0.5, []),
        ("A", 0.2, []),
        ("B", 0.2, [[2, 3, 4]]),
        ("B", 0.01, [[3, 4]]),
        ("C", 0.2, [[5, 6, 7, 8]]),
        ("C", 0.01, [[5, 6], [7, 8]]),
    ],
)
def test_refine_clusters_with_distance(
    df, lecture_group, distance_threshold, expected_amdt_idx_clusters
):
    tfidf_clusters = AmendmentsClusterFinder.find_similarity_clusters(
        amendments_df=df,
        group_by_columns=["Lecture"],
        text_column="Corps amdt",
        eps=0.5,
    )
    refined_clusters, _ = AmendmentsClusterFinder.refine_clusters_with_distance(
        amendments_df=df,
        group_by_columns=["Lecture"],
        text_column="Corps amdt",
        tfidf_clusters=tfidf_clusters,
        distance_threshold=distance_threshold,
    )
    assert refined_clusters[(lecture_group,)] == expected_amdt_idx_clusters
