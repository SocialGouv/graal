from unittest.mock import Mock, patch

import pandas as pd
import pytest

from amendements_intelligents.attribution.attribution_populator import (
    AttributionPopulator,
)
from amendements_intelligents.utils.text_utils import AttributionTextNormalizer


@pytest.fixture
def sample_amendments_df():
    return pd.DataFrame(
        {
            "amdt_idx": [1, 2, 3, 4, 5, 6, 7, 8, 9],
            "Corps amdt": [
                AttributionTextNormalizer.normalize_text(
                    "Modification du code civil article l. 1234"
                ),
                AttributionTextNormalizer.normalize_text(
                    "Dans le code penal article L.42"
                ),
                AttributionTextNormalizer.normalize_text(
                    "Simple texte sans code ni article"
                ),
                AttributionTextNormalizer.normalize_text("Code rural article L. 567"),
                AttributionTextNormalizer.normalize_text(
                    "art. 32 de la loi nº 96-50 du 24 janvier 1996 de l'infini et l'au-delà"
                ),
                AttributionTextNormalizer.normalize_text(
                    "article l. 321 de la loi nº 97-30 du 15 février 1997 de la blabla"
                ),
                AttributionTextNormalizer.normalize_text(
                    "article 56 de la loi nº 98-45 du 12 mars 1998 du machin bidule"
                ),
                AttributionTextNormalizer.normalize_text(
                    "article 12 de la loi nº 99-60 du 20 avril 1999 bob"
                ),
                AttributionTextNormalizer.normalize_text(
                    "article 20 de l'ordonnance nº 100-60 du 20 avril 1999 bla"
                ),
            ],
            "Num article": [
                "Article 1",
                "Article add. 2",
                "Article 3",
                "Article 4",
                "Article add. 1",
                "Article add. 1",
                "Article add. 2",
                "Article add. 4",
                "Article add. 5",
            ],
        }
    )


@pytest.fixture
def codes_articles_df():
    return pd.DataFrame(
        {
            "value": [
                AttributionTextNormalizer.normalize_text("civil"),
                AttributionTextNormalizer.normalize_text("penal"),
                AttributionTextNormalizer.normalize_text("rural"),
            ],
            "Articles": ["1234", "42", "567"],
            "Affectation (nom)": ["Expert1", "Expert2", "Expert3"],
        }
    )


@pytest.fixture
def laws_articles_df():
    return pd.DataFrame(
        {
            "value": [
                AttributionTextNormalizer.normalize_text("96-50 du 24 janvier 1996"),
                AttributionTextNormalizer.normalize_text("97-30 du 15 février 1997"),
                AttributionTextNormalizer.normalize_text("98-45 du 12 mars 1998"),
                AttributionTextNormalizer.normalize_text("99-60 du 20 avril 1999"),
            ],
            "Articles": ["32", "321", "56", "12"],
            "Affectation (nom)": ["Expert1", "Expert2", "Expert3", "Expert1"],
        }
    )


@pytest.fixture
def ordonnances_articles_df():
    return pd.DataFrame(
        {
            "value": [
                AttributionTextNormalizer.normalize_text("100-60 du 20 avril 1999"),
            ],
            "Articles": ["20"],
            "Affectation (nom)": ["Expert1"],
        }
    )


@pytest.fixture
def sample_keywords_df():
    return pd.DataFrame(
        {
            "Mots clés": ["civil", "penal", "rural"],
            "Affectation (nom)": ["Expert1", "Expert2", "Expert3"],
        }
    )


@pytest.fixture
def attribution_populator(
    sample_amendments_df,
    codes_articles_df,
    laws_articles_df,
    ordonnances_articles_df,
    sample_keywords_df,
):
    return AttributionPopulator(
        amendments_df=sample_amendments_df,
        attribution_mappings_when_empty=["DefaultExpert"],
        codes_articles_df=codes_articles_df,
        laws_articles_df=laws_articles_df,
        ordonnances_articles_df=ordonnances_articles_df,
        keywords_df=sample_keywords_df,
        name_to_email_mapping={
            "Expert1": "expert1@example.com",
            "Expert2": "expert2@example.com",
            "Expert3": "expert3@example.com",
            "DefaultExpert": "default@example.com",
        },
        ignore_non_interstitial_amdts=False,
    )


def test_match_codes_and_articles_to_amendments(attribution_populator):
    matches = attribution_populator.match_codes_and_articles_to_amendments()

    assert len(matches) == 3
    assert matches[1]["matching_entities"] == {"civil"}
    assert matches[1]["matching_articles"] == {"1234"}
    assert matches[2]["matching_entities"] == {"penal"}
    assert matches[2]["matching_articles"] == {"42"}
    assert matches[4]["matching_entities"] == {"rural"}
    assert matches[4]["matching_articles"] == {"567"}


def test_match_laws_and_articles_to_amendments(attribution_populator):
    matches = attribution_populator.match_laws_and_articles_to_amendments()

    assert len(matches) == 4
    assert matches[5]["matching_entities"] == {"96-50 du 24 janvier 1996"}
    assert matches[5]["matching_articles"] == {"32"}
    assert matches[6]["matching_entities"] == {"97-30 du 15 fevrier 1997"}
    assert matches[6]["matching_articles"] == {"321"}
    assert matches[7]["matching_entities"] == {"98-45 du 12 mars 1998"}
    assert matches[7]["matching_articles"] == {"56"}
    assert matches[8]["matching_entities"] == {"99-60 du 20 avril 1999"}
    assert matches[8]["matching_articles"] == {"12"}


def test_match_ordonnances_and_articles_to_amendments(attribution_populator):
    matches = attribution_populator.match_ordonnances_and_articles_to_amendments()

    assert len(matches) == 1
    assert matches[9]["matching_entities"] == {"100-60 du 20 avril 1999"}
    assert matches[9]["matching_articles"] == {"20"}


def test_filter_matching_entities_and_articles(attribution_populator):
    code_matches = attribution_populator.match_codes_and_articles_to_amendments()
    law_matches = attribution_populator.match_laws_and_articles_to_amendments()
    ordonnance_matches = (
        attribution_populator.match_ordonnances_and_articles_to_amendments()
    )

    matches = {
        **code_matches,
        **law_matches,
        **ordonnance_matches,
    }
    matching_rows = attribution_populator.filter_matching_entities_and_articles(matches)

    assert len(matching_rows) == 8
    assert "Affectation (nom)" in matching_rows.columns
    assert "amdt_idx" in matching_rows.columns


def test_aggregate_matches_by_amendment(attribution_populator):
    matches = attribution_populator.match_codes_and_articles_to_amendments()
    matching_rows = attribution_populator.filter_matching_entities_and_articles(matches)
    aggregated = attribution_populator.aggregate_matches_by_amendment(matching_rows)

    assert len(aggregated) == 3
    assert all(isinstance(x, list) for x in aggregated["Affectation (nom)"])


@pytest.mark.parametrize(
    "input_row,expected",
    [
        (pd.Series({"Affectation (nom)": None}, name=0), ["Expert1", "Expert2"]),
        (pd.Series({"Affectation (nom)": ["Expert1"]}, name=0), ["Expert1"]),
        (pd.Series({"Affectation (nom)": ["Expert1", "Expert3"]}, name=0), ["Expert1"]),
        (pd.Series({"Affectation (nom)": ["Expert3"]}, name=0), ["Expert3"]),
    ],
)
def test_update_with_keyword_matches(input_row, expected):
    keyword_matches_df = pd.DataFrame(
        {"Affectation (nom)": [["Expert1", "Expert2"]]}, index=[0]
    )
    result = AttributionPopulator.update_with_keyword_matches(
        input_row, keyword_matches_df
    )
    assert result == expected


@patch("amendements_intelligents.attribution.attribution_populator.Pool")
def test_parallel_keyword_fuzzy_matching(mock_pool, attribution_populator):
    mock_pool_instance = Mock()
    mock_pool_instance.starmap.return_value = [[{"Keyword": "civil", "amdt_idx": "1"}]]
    mock_pool.return_value.__enter__.return_value = mock_pool_instance

    results = attribution_populator.parallel_keyword_fuzzy_matching(
        keywords={"civil"}, matcher=Mock(), threshold=75
    )

    assert len(results) == 1
    assert results[0]["Keyword"] == "civil"


def test_calculate_ratio_of_lists():
    df = pd.DataFrame(
        {"Affectation (nom)": [["Expert1", "Expert2"], ["Expert1"], [], None]}
    )
    ratio = AttributionPopulator.calculate_ratio_of_lists(df)
    assert ratio == 0.5  # 1 list with >1 element out of 2 non-empty lists


def test_populate_end_to_end(attribution_populator):
    result_df = attribution_populator.populate()

    assert len(result_df) == 9
    assert "Affectation (nom)" in result_df.columns
    assert "Affectation (email)" in result_df.columns
    assert "Commentaires" in result_df.columns


@pytest.mark.parametrize(
    "test_input,expected",
    [
        (pd.Series({"Commentaires": None}), "New comment"),
        (pd.Series({"Commentaires": "Existing"}), "Existing\nNew comment"),
        (pd.Series({}), "New comment"),
    ],
)
def test_append_comment_to_amendment(test_input, expected):
    df = pd.DataFrame([test_input])
    AttributionPopulator.append_comment_to_amendment(df, 0, "New comment")
    assert df.at[0, "Commentaires"] == expected
