import pandas as pd
import pytest

from amendements_intelligents.clustering.plfss_cluster_finder import PLFSSClusterFinder


@pytest.fixture
def df():
    data = {
        "Lecture": ["A", "A", "B", "B", "B", "C", "C", "C", "C"],
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


@pytest.fixture
def cluster_finder(df):
    cluster_finder = PLFSSClusterFinder(df)
    cluster_finder._vectorize_data()  # Ensure vectorizer is fitted before tests
    return cluster_finder


@pytest.mark.parametrize(
    "lecture_group, expected_shape",
    [
        ("A", (2, 2)),
        ("B", (3, 3)),
        ("C", (4, 4)),
    ],
)
def test_compute_distance_matrix(cluster_finder, lecture_group, expected_shape):
    cluster_finder._transform_lecture_group(lecture_group)
    cluster_finder._compute_distance_matrix(lecture_group)
    assert lecture_group in cluster_finder.distance_matrix_per_lecture
    assert (
        cluster_finder.distance_matrix_per_lecture[lecture_group].shape
        == expected_shape
    )


@pytest.mark.parametrize(
    "lecture_group",
    [
        "A",
        "B",
        "C",
    ],
)
def test_transform_lecture_group(cluster_finder, df, lecture_group):
    cluster_finder._transform_lecture_group(lecture_group)
    assert lecture_group in cluster_finder.vectors_per_lecture
    assert cluster_finder.vectors_per_lecture[lecture_group].shape[0] == len(
        df[df["Lecture"] == lecture_group]
    )


@pytest.mark.parametrize(
    "lecture_group, eps, expected_clusters",
    [
        ("A", 1, [[0, 1]]),
        ("A", 0.5, []),
        ("B", 0.5, [[0, 1, 2]]),
        ("C", 0.5, [[0, 1, 2, 3]]),
        ("A", 0.2, []),
        ("B", 0.2, [[1, 2]]),
        ("C", 0.2, [[0, 1], [2, 3]]),
    ],
)
def test_find_similarity_clusters(
    cluster_finder, lecture_group, eps, expected_clusters
):
    tfidf_clusters_per_lecture = cluster_finder.find_similarity_clusters(eps=eps)
    assert tfidf_clusters_per_lecture[lecture_group] == expected_clusters


@pytest.mark.parametrize(
    "lecture_group, eps, expected_clusters",
    [
        ("A", 1, [[0, 1]]),
        ("A", 0.5, []),
        ("B", 0.5, [[0, 1, 3]]),
        ("C", 0.5, [[0, 1, 2, 3]]),
        ("A", 0.2, []),
        ("B", 0.2, [[1, 3]]),
        ("C", 0.2, [[0, 1], [2, 3]]),
    ],
)
def test_find_similarity_clusters_messy_data(lecture_group, eps, expected_clusters):
    data = {
        "Lecture": ["C", "A", "A", "B", "B", "C", "C", "B", "B", "C"],
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
    cluster_finder = PLFSSClusterFinder(df)
    cluster_finder._vectorize_data()  # Ensure vectorizer is fitted before tests
    tfidf_clusters_per_lecture = cluster_finder.find_similarity_clusters(eps=eps)
    assert tfidf_clusters_per_lecture[lecture_group] == expected_clusters


@pytest.mark.parametrize(
    "lecture_group, threshold, expected_clusters",
    [
        ("A", 0.5, []),
        ("A", 0.2, []),
        ("B", 0.2, [[0, 1, 2]]),
        ("B", 0.01, [[1, 2]]),
        ("C", 0.2, [[0, 1, 2, 3]]),
        ("C", 0.01, [[0, 1], [2, 3]]),
    ],
)
def test_refine_clusters_for_exact_match(
    cluster_finder, lecture_group, threshold, expected_clusters
):
    cluster_finder.find_similarity_clusters(eps=0.5)
    refined_clusters = cluster_finder.refine_clusters_with_exact_match(
        threshold=threshold
    )
    assert refined_clusters[lecture_group] == expected_clusters
