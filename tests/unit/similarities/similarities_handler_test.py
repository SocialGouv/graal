import pandas as pd
import pytest


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
