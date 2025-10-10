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


# Helper functions for large cluster tests


def generate_similar_amendments(
    base_text: str,
    count: int,
    variation_type: str = "word_substitution",
) -> pd.DataFrame:
    """
    Generate a DataFrame with similar amendments for testing.

    Args:
        base_text: Base amendment text
        count: Number of amendments to generate
        variation_type: How to vary texts ("word_substitution", "minor_edits", "identical")

    Returns:
        DataFrame with columns: amdt_idx, Corps amdt, Lecture
    """
    amendments = []

    if variation_type == "identical":
        # All texts identical
        for i in range(count):
            amendments.append(
                {"amdt_idx": i, "Corps amdt": base_text, "Lecture": "TEST"}
            )
    elif variation_type == "minor_edits":
        # Add/remove/change 1-3 characters
        for i in range(count):
            if i % 3 == 0:
                text = base_text + f" {i}"
            elif i % 3 == 1:
                text = base_text.replace("article", f"article {i}")
            else:
                text = base_text[:10] + f"{i}" + base_text[10:]
            amendments.append({"amdt_idx": i, "Corps amdt": text, "Lecture": "TEST"})
    else:  # word_substitution
        # Replace 1-2 words to create similar but distinct texts
        numbers = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]
        verbs = ["modifié", "remplacé", "complété", "supprimé", "abrogé"]
        for i in range(count):
            article_num = numbers[i % len(numbers)]
            verb = verbs[i % len(verbs)]
            text = f"L'article {article_num} du code du travail est {verb}"
            amendments.append({"amdt_idx": i, "Corps amdt": text, "Lecture": "TEST"})

    return pd.DataFrame(amendments)


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
    refined_clusters, _ = AmendmentsClusterFinder.refine_with_levenshtein(
        amendments_df=df,
        group_by_columns=["Lecture"],
        text_column="Corps amdt",
        tfidf_clusters=tfidf_clusters,
        distance_threshold=distance_threshold,
    )
    assert refined_clusters[(lecture_group,)] == expected_amdt_idx_clusters


# Tests for large cluster refinement


def test_large_cluster_subdivision_with_levenshtein_refinement():
    """
    Subdivision happens in TF-IDF phase, then Levenshtein refines.

    With 50 similar amendments, the workflow is:
    1. find_similarity_clusters() automatically subdivides into multiple clusters ≤30
    2. refine_with_levenshtein() applies Levenshtein to those pre-subdivided clusters
    3. similarity_percentages dict is populated (proves Levenshtein was applied)

    This test validates the complete two-phase architecture.
    """
    # Generate 50 similar amendments
    base_text = "L'article 1 du code du travail est modifié"
    df = generate_similar_amendments(base_text, 50, variation_type="word_substitution")

    # Phase 1: Complete TF-IDF clustering (with automatic subdivision)
    tfidf_clusters = AmendmentsClusterFinder.find_similarity_clusters(
        amendments_df=df,
        group_by_columns=["Lecture"],
        text_column="Corps amdt",
        eps=0.5,
    )

    # Verify TF-IDF phase subdivided the large cluster automatically
    assert ("TEST",) in tfidf_clusters, "Expected cluster for TEST lecture"
    assert len(tfidf_clusters[("TEST",)]) > 1, (
        "Expected multiple clusters after automatic subdivision in TF-IDF phase, "
        f"but got {len(tfidf_clusters[('TEST',)])} cluster(s)"
    )

    # Verify ALL TF-IDF clusters are ≤30 (ready for Levenshtein)
    for cluster in tfidf_clusters[("TEST",)]:
        assert (
            len(cluster) <= AmendmentsClusterFinder.MAX_CLUSTER_SIZE_FOR_LEVENSHTEIN
        ), (
            f"TF-IDF phase should guarantee all clusters ≤{AmendmentsClusterFinder.MAX_CLUSTER_SIZE_FOR_LEVENSHTEIN}, "
            f"but found cluster with {len(cluster)} amendments"
        )

    # Phase 2: Levenshtein refinement (no subdivision, just refinement)
    refined_clusters, similarity_percentages = (
        AmendmentsClusterFinder.refine_with_levenshtein(
            amendments_df=df,
            group_by_columns=["Lecture"],
            text_column="Corps amdt",
            tfidf_clusters=tfidf_clusters,
            distance_threshold=0.2,
        )
    )

    # Verify Levenshtein was applied (similarity_percentages populated)
    assert (
        len(similarity_percentages) > 0
    ), "Expected similarity_percentages to be populated after Levenshtein refinement"

    # Verify at least some amendment pairs have similarity percentages
    total_pairs = sum(len(pairs) for pairs in similarity_percentages.values())
    assert (
        total_pairs > 0
    ), "Expected at least some amendment pairs to have similarity percentages"

    # Verify final clusters are still ≤30
    for cluster in refined_clusters[("TEST",)]:
        assert (
            len(cluster) <= AmendmentsClusterFinder.MAX_CLUSTER_SIZE_FOR_LEVENSHTEIN
        ), (
            f"Expected all final clusters ≤{AmendmentsClusterFinder.MAX_CLUSTER_SIZE_FOR_LEVENSHTEIN}, "
            f"but found cluster with {len(cluster)} amendments"
        )
