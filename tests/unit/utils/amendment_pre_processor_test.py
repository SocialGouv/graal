import json
from pathlib import Path

import pandas as pd
import pytest

from graal.utils.amendment_pre_processor import AmendmentPreProcessor


def test_replace_common_amendment_bodies():
    df = pd.DataFrame(
        {
            "Corps amdt": [
                "Supprimer l'article liminaire.",
                "supprimer l'article liminaire",
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
                "Article 1",
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
    amendments_processor = AmendmentPreProcessor

    preprocessed_amendments_df = amendments_processor.handle_common_amendment_bodies(df)

    expected_processed_legistique = [
        "Supprimer cet article. Article 1",
        "Supprimer cet article. Article 1",
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
    processor = AmendmentPreProcessor
    result_df = processor.drop_empty_rows_in_columns(
        amendments_df=df, columns_to_filter=["Corps amdt"]
    )

    expected_df = pd.DataFrame(
        {
            "Corps amdt": ["Not empty1", "Not empty2"],
            "Num article": ["Article 1", "Article 4"],
        }
    )

    pd.testing.assert_frame_equal(
        result_df.reset_index(drop=True),
        expected_df.reset_index(drop=True),
    )


def test_normalize_amendments():
    df = pd.DataFrame(
        {
            "test1": [
                "fooàé 1",
                'bar"\\[}  2',
                """
                Hello
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

    amendment_processor = AmendmentPreProcessor

    normalized_df = amendment_processor.normalize_amendments(
        amendments_df=df, columns_to_normalize=["test1"]
    )

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
                        "Another amendment that is too long to be appended to!",
                        "amendement de coordination.",
                    ],
                    "Corps amdt": ["Body 1", "Body 2", "Body 3", "Body 4"],
                }
            ),
            pd.DataFrame(
                {
                    "Exposé amdt": [
                        "Amendement rédactionnel. Body 1",
                        "A small amendment Body 2",
                        "Another amendment that is too long to be appended to!",
                        "amendement de coordination. Body 4",
                    ],
                    "Corps amdt": ["Body 1", "Body 2", "Body 3", "Body 4"],
                    "is_redactional": [True, False, False, True],
                }
            ),
        ),
        (
            pd.DataFrame(
                {
                    "Exposé amdt": [
                        "This is a long exposé amdt but it contains aMEndement rédactionnel so it should be detected as such and appended to!",
                        "Short",
                    ],
                    "Corps amdt": ["Body B", "Body C"],
                }
            ),
            pd.DataFrame(
                {
                    "Exposé amdt": [
                        "This is a long exposé amdt but it contains aMEndement rédactionnel so it should be detected as such and appended to! Body B",
                        "Short Body C",
                    ],
                    "Corps amdt": ["Body B", "Body C"],
                    "is_redactional": [True, False],
                }
            ),
        ),
    ],
)
def test_handle_common_amendment_expose_and_redactional(input_df, expected_df):
    amendment_processor = AmendmentPreProcessor
    result_df = amendment_processor.handle_common_amendment_expose_and_redactional(
        amendments_df=input_df
    )
    pd.testing.assert_frame_equal(result_df, expected_df)


def test_clean_up_original_amendments():
    amendment_processor = AmendmentPreProcessor
    original_amendments_df = pd.DataFrame(
        {
            "chambre": ["A", "B"],
            "legislature": [1, 2],
            "corps": ["<p>Corps 1</p>", "<p>Corps 2</p>"],
            "expose": ["<p>Expose 1</p>", "<p>Expose 2</p>"],
            "objet": ["<p>Objet 1</p>", "<p>Objet 2</p>"],
            "sort": ["<p>Sort 1</p>", "<p>Sort 2</p>"],
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
            "Objet amdt": ["Objet 1", "Objet 2"],
            "Sort": ["Sort 1", "Sort 2"],
            "Num article": ["Article 1", "Article 2"],
            "Corps amdt": ["Corps 1", "Corps 2"],
            "Corps amdt original": ["<p>Corps 1</p>", "<p>Corps 2</p>"],
            "Exposé amdt": ["Expose 1", "Expose 2"],
            "Allotissement": ["1,2", "18,29"],
        }
    )

    result_amendments_df = amendment_processor.clean_up_json_columns(
        amendements_df=original_amendments_df
    )
    result_amendments_df = amendment_processor.remap_columns_in_json_amendments(
        amendments_df=result_amendments_df
    )

    pd.testing.assert_frame_equal(
        result_amendments_df.reset_index(drop=True).sort_index(axis=1),
        expected_work_amendments_df.reset_index(drop=True).sort_index(axis=1),
    )


def test_clear_columns_to_be_overridden():
    df = pd.DataFrame(
        {
            "Corps amdt": ["Body 1", "Body 2"],
            "Exposé amdt": ["Expose 1", "Expose 2"],
            "Objet amdt": ["Objet 1", "Objet 2"],
            "Affectation (email)": ["email 1", "email 2"],
            "Affectation (nom)": ["nom 1", "nom 2"],
            "Entité Pilote": ["Entité 1", "Entité 2"],
            "Allotissement": [2, 1],
        }
    )
    expected_df = pd.DataFrame(
        {
            "Corps amdt": ["Body 1", "Body 2"],
            "Exposé amdt": ["Expose 1", "Expose 2"],
            "Objet amdt": ["Objet 1", "Objet 2"],
            "Affectation (email)": [None, None],
            "Affectation (nom)": [None, None],
            "Entité Pilote": [None, None],
            "Allotissement": [None, None],
        }
    )

    amendment_processor = AmendmentPreProcessor
    prepared_df = amendment_processor.clear_columns_to_be_overridden(
        df,
        columns_to_clear=[
            "Allotissement",
            "Affectation (email)",
            "Affectation (nom)",
            "Entité Pilote",
        ],
    )

    pd.testing.assert_frame_equal(
        prepared_df.reset_index(drop=True),
        expected_df.reset_index(drop=True),
    )


@pytest.mark.parametrize(
    "input_df, acronym_mapping, columns_to_normalize, expected_df",
    [
        (
            pd.DataFrame(
                {
                    "Corps amdt": [
                        "This is an amendment with an acronym ABC.",
                        "Another amendment with acronym XYZ.",
                        "No acronym here.",
                    ],
                    "Exposé amdt": [
                        "Exposé with acronym ABC.",
                        "Another exposé with XYZ.",
                        "No acronym in exposé.",
                    ],
                }
            ),
            {
                "ABC": "A Big Change",
                "XYZ": "Xylophone Zebra Yak",
            },
            ["Corps amdt", "Exposé amdt"],
            pd.DataFrame(
                {
                    "Corps amdt": [
                        "This is an amendment with an acronym A Big Change.",
                        "Another amendment with acronym Xylophone Zebra Yak.",
                        "No acronym here.",
                    ],
                    "Exposé amdt": [
                        "Exposé with acronym A Big Change.",
                        "Another exposé with Xylophone Zebra Yak.",
                        "No acronym in exposé.",
                    ],
                }
            ),
        ),
        (
            pd.DataFrame(
                {
                    "Corps amdt": [
                        "Amendment with acronym DEF.",
                        "Another one with GHI.",
                    ],
                    "Exposé amdt": [
                        "Exposé with DEF.",
                        "Exposé with GHI.",
                    ],
                }
            ),
            {
                "DEF": "Definite Explanation Found",
                "GHI": "Great Historical Insight",
            },
            ["Corps amdt", "Exposé amdt"],
            pd.DataFrame(
                {
                    "Corps amdt": [
                        "Amendment with acronym Definite Explanation Found.",
                        "Another one with Great Historical Insight.",
                    ],
                    "Exposé amdt": [
                        "Exposé with Definite Explanation Found.",
                        "Exposé with Great Historical Insight.",
                    ],
                }
            ),
        ),
        (
            pd.DataFrame(
                {
                    "Corps amdt": [
                        "Amendment with acronym JKL.",
                        "Another one with MNO.",
                    ],
                    "Exposé amdt": [
                        "Exposé with JKL.",
                        "Exposé with MNO.",
                    ],
                }
            ),
            {
                "JKL": "Just Kidding, Literally",
                "MNO": "Many New Opportunities",
            },
            ["Corps amdt"],
            pd.DataFrame(
                {
                    "Corps amdt": [
                        "Amendment with acronym Just Kidding, Literally.",
                        "Another one with Many New Opportunities.",
                    ],
                    "Exposé amdt": [
                        "Exposé with JKL.",
                        "Exposé with MNO.",
                    ],
                }
            ),
        ),
    ],
)
def test_replace_acronyms(input_df, acronym_mapping, columns_to_normalize, expected_df):
    amendment_processor = AmendmentPreProcessor

    result_df = amendment_processor.replace_acronyms(
        amendments_df=input_df,
        acronym_mapping=acronym_mapping,
        columns_to_normalize=columns_to_normalize,
    )

    pd.testing.assert_frame_equal(
        result_df.reset_index(drop=True),
        expected_df.reset_index(drop=True),
    )


def test_load_amendments_json(mocker):
    mocker.patch(
        "builtins.open",
        mocker.mock_open(
            read_data=json.dumps(
                {
                    "amendements": [
                        {
                            "date_derniere_modif": "2023-01-01 00:00:01.000",
                            "some_field": "value1",
                        },
                        {
                            "date_derniere_modif": "",
                            "some_field": "value2",
                        },
                    ]
                }
            )
        ),
    )
    mocker.patch(
        "graal.utils.amendment_pre_processor.AmendmentPreProcessor.clean_up_json_columns",
        side_effect=lambda x: x,
    )

    input_files = [Path("file1.json"), Path("file2.json"), Path("file3.json")]
    file_config = {
        Path("file1.json"): {
            "default_processing_timestamp": 1234567890,
            "origin_project": "PLFSS",
        },
        Path("file2.json"): {
            "default_processing_timestamp": 1234567890,
            "origin_project": "PPL Retraites",
        },
        Path("file3.json"): {
            "default_processing_timestamp": 1234567890,
            "origin_project": "PLACSS",
        },
    }

    result_df = AmendmentPreProcessor.load_amendments_json(input_files, file_config)

    expected_df = pd.DataFrame(
        {
            "date_derniere_modif": [
                "2023-01-01 00:00:01.000",
                "",
                "2023-01-01 00:00:01.000",
                "",
                "2023-01-01 00:00:01.000",
                "",
            ],
            "some_field": ["value1", "value2", "value1", "value2", "value1", "value2"],
            "origin_project": [
                "PLFSS",
                "PLFSS",
                "PPL Retraites",
                "PPL Retraites",
                "PLACSS",
                "PLACSS",
            ],
            "timestamp": [
                1672531201,
                1234567890,
                1672531201,
                1234567890,
                1672531201,
                1234567890,
            ],
            "amdt_idx": [0, 1, 2, 3, 4, 5],
        }
    )

    pd.testing.assert_frame_equal(
        result_df.reset_index(drop=True), expected_df.reset_index(drop=True)
    )


def test_load_amendments_excel(mocker):
    mocker.patch(
        "pandas.read_excel",
        side_effect=[
            pd.DataFrame(
                {
                    "date_derniere_modif": ["2023-01-01 00:00:01.000", ""],
                    "some_field": ["value1", "value2"],
                }
            ),
            pd.DataFrame(
                {
                    "date_derniere_modif": ["2023-01-01 00:00:01.000", ""],
                    "some_field": ["value3", "value4"],
                }
            ),
        ],
    )

    input_files = [Path("file1.xlsx"), Path("file2.xlsx")]
    file_config = {
        Path("file1.xlsx"): {
            "default_processing_timestamp": 1234567890,
            "origin_project": "PLFSS",
        },
        Path("file2.xlsx"): {
            "default_processing_timestamp": 1234567890,
            "origin_project": "PPL Retraites",
        },
    }

    result_df = AmendmentPreProcessor.load_amendments_excel(input_files, file_config)

    expected_df = pd.DataFrame(
        {
            "date_derniere_modif": [
                "2023-01-01 00:00:01.000",
                "",
                "2023-01-01 00:00:01.000",
                "",
            ],
            "some_field": ["value1", "value2", "value3", "value4"],
            "origin_project": ["PLFSS", "PLFSS", "PPL Retraites", "PPL Retraites"],
            "timestamp": [
                1234567890,
                1234567890,
                1234567890,
                1234567890,
            ],
            "amdt_idx": [0, 1, 2, 3],
        }
    )

    pd.testing.assert_frame_equal(
        result_df.reset_index(drop=True), expected_df.reset_index(drop=True)
    )


def test_concatenate_dataframes():
    df1 = pd.DataFrame(
        {
            "amdt_idx": [0, 1],
            "col1": ["A", "B"],
            "col2": ["C", "D"],
        }
    )

    df2 = pd.DataFrame(
        {
            "amdt_idx": [0, 1],
            "col1": ["E", "F"],
            "col3": ["G", "H"],
        }
    )

    expected_df = pd.DataFrame(
        {
            "amdt_idx": [0, 1, 2, 3],
            "col1": ["A", "B", "E", "F"],
            "col2": ["C", "D", None, None],
            "col3": [None, None, "G", "H"],
        }
    )

    result_df = AmendmentPreProcessor.concatenate_dataframes(df1, df2)

    pd.testing.assert_frame_equal(
        result_df.reset_index(drop=True), expected_df.reset_index(drop=True)
    )
