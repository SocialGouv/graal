import pandas as pd
import pytest

from amendements_intelligents.data_handlers.plfss_pre_processor import (
    PLFSSPreProcessor,
)


@pytest.fixture
def df():
    return pd.DataFrame(
        {
            "Corps amdt": [
                "Supprimer cet article.",
                "Some other text",
                "Supprimer l’alinéa 19.",
                "Supprimer les alinéas 123 et 12",
                "Supprimer les alinéas 3 à 500",
                "Long enough to stay the same, Long enough to stay the same, Long enough to stay the same, Long enough to stay the same",
                'Long enough to stay the same, Long enough to stay the same, Long enough to stay the same, Long enough to stay the same but it contains "Supprimer les alinéas 1 à 10"',
            ],
            "Num article": [
                "Article 1",
                "Article 2",
                "Article 3",
                "Article 4",
                "Article 5",
                "Article 6",
                "Article 7",
            ],
        }
    )


def test_replace_common_amendment_bodies(df):
    plfss_processor = PLFSSPreProcessor()
    plfss_processor.work_amendments_df = df.copy()

    plfss_processor.handle_common_amendment_bodies()
    preprocessed_amendments_df = plfss_processor.work_amendments_df

    expected_processed_legistique = [
        "Supprimer cet article. Article 1",
        "Some other text Article 2",
        "Supprimer l’alinéa 19. Article 3",
        "Supprimer les alinéas 123 et 12 Article 4",
        "Supprimer les alinéas 3 à 500 Article 5",
        "Long enough to stay the same, Long enough to stay the same, Long enough to stay the same, Long enough to stay the same",
        'Long enough to stay the same, Long enough to stay the same, Long enough to stay the same, Long enough to stay the same but it contains "Supprimer les alinéas 1 à 10" Article 7',
    ]
    assert (
        preprocessed_amendments_df["Corps amdt"].tolist()
        == expected_processed_legistique
    )


def test_remove_useless_amendments():
    df = pd.DataFrame(
        {
            "Corps amdt": [
                "Not empty1",
                None,
                None,
                "Not empty2",
            ],
            "Num article": [
                "Article 1",
                "Article 2",
                "Article 3",
                "Article 4",
            ],
        }
    )
    processor = PLFSSPreProcessor()
    processor.work_amendments_df = df.copy()

    processor.remove_empty_rows_for_given_columns(columns_to_filter_with=["Corps amdt"])

    expected_df = pd.DataFrame(
        {
            "Corps amdt": ["Not empty1", "Not empty2"],
            "Num article": ["Article 1", "Article 4"],
        }
    )

    pd.testing.assert_frame_equal(
        processor.work_amendments_df.reset_index(drop=True),
        expected_df.reset_index(drop=True),
    )


def test_normalize_plfss(df):
    df = pd.DataFrame(
        {
            "test1": [
                "fooàé 1",
                'bar"\\[}  2',
                """
                Hello

                la perte de recettes pour this should be removed.
                world.
                """,
            ],
            "test2": [
                "fooàé 1",
                'bar"\\[}  2',
                "foo",
            ],
        }
    )

    expected_normalized_df = pd.DataFrame(
        {
            "test1": [
                "fooae 1",
                "bar 2",
                "hello world",
            ],
            "test2": [
                "fooàé 1",
                'bar"\\[}  2',
                "foo",
            ],
        }
    )

    plfss_processor = PLFSSPreProcessor()
    plfss_processor.work_amendments_df = df.copy()

    normalized_df = plfss_processor.normalize_plfss(columns_to_normalize=["test1"])

    pd.testing.assert_frame_equal(
        normalized_df.reset_index(drop=True),
        expected_normalized_df.reset_index(drop=True),
    )
