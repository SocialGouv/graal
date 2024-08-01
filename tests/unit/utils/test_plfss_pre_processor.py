import pandas as pd
import pytest

from amendements_intelligents.utils.plfss_pre_processor import (
    PLFSSPreProcessor,
)


def test_replace_common_amendment_bodies():
    df = pd.DataFrame(
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


def test_normalize_plfss():
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


@pytest.mark.parametrize(
    "input_df, expected_df",
    [
        (
            pd.DataFrame(
                {
                    "Exposé amdt": [
                        "Amendement rédactionnel.",
                        "A small amendment",
                        "Another amendment that is too long to be replaced",
                    ],
                    "Corps amdt": ["Body 1", "Body 2", "Body 3"],
                }
            ),
            pd.DataFrame(
                {
                    "Exposé amdt": [
                        "Body 1",
                        "Body 2",
                        "Another amendment that is too long to be replaced",
                    ],
                    "Corps amdt": ["Body 1", "Body 2", "Body 3"],
                }
            ),
        ),
        (
            pd.DataFrame(
                {
                    "Exposé amdt": [
                        "This is a long exposé amdt but it contains aMEndement rédactionnel so it should be replaced!",
                        "Short",
                    ],
                    "Corps amdt": ["Body B", "Body C"],
                }
            ),
            pd.DataFrame(
                {
                    "Exposé amdt": [
                        "Body B",
                        "Body C",
                    ],
                    "Corps amdt": ["Body B", "Body C"],
                }
            ),
        ),
    ],
)
def test_handle_common_amendment_expose(input_df, expected_df):
    plfss_processor = PLFSSPreProcessor()
    plfss_processor.work_amendments_df = input_df.copy()
    result_df = plfss_processor.handle_common_amendment_expose()
    pd.testing.assert_frame_equal(result_df, expected_df)


def test_clean_up_original_amendments():
    plfss_processor = PLFSSPreProcessor()
    plfss_processor.original_amendments_df = pd.DataFrame(
        {
            "chambre": ["A", "B"],
            "legislature": [1, 2],
            "corps": ["<p>Corps 1</p>", "<p>Corps 2</p>"],
            "expose": ["<p>Expose 1</p>", "<p>Expose 2</p>"],
            "sort": ["<p>Sort 1</p>", "<p>Sort 2</p>"],
            "reponse": ["<p>Réponse 1</p>", "<p>Réponse 2</p>"],
            "computed_batch": [[1, 2], [18, 29]],
            "num": [1, 2],
            "article": ["Article 1", "Article 2"],
        }
    )

    expected_work_amendments_df = pd.DataFrame(
        {
            "chambre": ["A", "B"],
            "legislature": [1, 2],
            "Lecture": ["A 1", "B 2"],
            "Num amdt": [1, 2],
            "Sort": ["Sort 1", "Sort 2"],
            "Réponse": ["Réponse 1", "Réponse 2"],
            "Num article": ["Article 1", "Article 2"],
            "Corps amdt": ["Corps 1", "Corps 2"],
            "Exposé amdt": ["Expose 1", "Expose 2"],
            "Allotissement": ["1,2", "18,29"],
        }
    )

    result_amendments_df = plfss_processor.clean_up_original_amendments()

    pd.testing.assert_frame_equal(
        result_amendments_df.reset_index(drop=True).sort_index(axis=1),
        expected_work_amendments_df.reset_index(drop=True).sort_index(axis=1),
    )
