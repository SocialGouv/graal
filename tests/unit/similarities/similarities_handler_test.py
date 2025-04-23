import pandas as pd

from graal.similarities.similarities_handler import SimilaritiesHandler


def test_calculate_similarity_percentages():
    # Sample input dataframe
    normalized_amdt_df = pd.DataFrame(
        {
            "amdt_idx": [1, 2, 3],
            "Num amdt": [101, 102, 103],
            "Corps amdt": [
                "This is amendment one",
                "This is amendment one with a small change",
                "This is a completely different amendment",
            ],
        }
    )

    # Sample clusters
    allotted_amdt_clusters = {("Lecture1",): [[1, 2, 3]]}

    # Call the function
    result = SimilaritiesHandler.calculate_similarity_percentages(
        normalized_amdt_df, allotted_amdt_clusters
    )

    # Check that the result has the expected structure
    assert 1 in result
    assert 2 in result
    assert 3 in result

    # Check that the similarity percentages are reasonable
    assert result[1][2] > 50  # Amendment 1 and 2 should be quite similar
    assert result[1][3] < 50  # Amendment 1 and 3 should be less similar
    assert result[2][3] < 50  # Amendment 2 and 3 should be less similar


def test_update_comments_with_similarities():
    # Sample input dataframe
    amendments_df = pd.DataFrame(
        {
            "amdt_idx": [1, 2, 3],
            "Num amdt": [101, 102, 103],
            "Commentaires": ["Existing comment", "", None],
        }
    )

    # Sample similarity percentages
    similarity_percentages = {
        1: {2: 85.5, 3: 42.3},
        2: {1: 85.5, 3: 40.1},
        3: {1: 42.3, 2: 40.1},
    }

    result_df = SimilaritiesHandler.update_comments_with_similarities(
        amendments_df, similarity_percentages, threshold=0.8
    )

    # Check that the comments were updated correctly
    # Only similarities >= 80% should be included
    assert "Existing comment" in result_df.loc[0, "Commentaires"]
    assert "Amdt similaires : 102 (86%)" in result_df.loc[0, "Commentaires"]
    assert "103 (42%)" not in result_df.loc[0, "Commentaires"]
    assert "Amdt similaires : 101 (86%)" in result_df.loc[1, "Commentaires"]
    assert "103 (40%)" not in result_df.loc[1, "Commentaires"]
    # Amendment 3 should not have any comments since none of its similarities are >= 80%
    assert (
        pd.isna(result_df.loc[2, "Commentaires"])
        or result_df.loc[2, "Commentaires"] == ""
    )
