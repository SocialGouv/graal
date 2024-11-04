from unittest.mock import Mock, patch

import pandas as pd
import pytest

from amendements_intelligents.attribution.attribution_populator import (
    AttributionPopulator,
)
from amendements_intelligents.utils.text_utils import AttributionTextNormalizer


def test_match_codes_and_articles_to_amendments_body():
    # Data specific to this test
    sample_amendments_df = pd.DataFrame(
        {
            "amdt_idx": [1, 2, 3],
            "Corps amdt": [
                AttributionTextNormalizer.normalize_text(
                    "Modification du code civil article l. 1234"
                ),
                AttributionTextNormalizer.normalize_text(
                    "Dans le code penal article L.42"
                ),
                AttributionTextNormalizer.normalize_text("Code rural article L. 567"),
            ],
        }
    )
    codes_articles_df = pd.DataFrame(
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

    # Instantiate AttributionPopulator with minimal configuration
    attribution_populator = AttributionPopulator(
        amendments_df=sample_amendments_df,
        attribution_mappings_when_empty=["DefaultExpert"],
        codes_articles_df=codes_articles_df,
        laws_articles_df=pd.DataFrame(),
        ordonnances_articles_df=pd.DataFrame(),
        keywords_df=pd.DataFrame(),
        name_to_email_mapping={
            "Expert1": "expert1@example.com",
            "Expert2": "expert2@example.com",
            "Expert3": "expert3@example.com",
            "DefaultExpert": "default@example.com",
        },
        ignore_non_interstitial_amdts=False,
    )

    matches = attribution_populator.match_codes_and_articles_to_amendments("Corps amdt")

    assert len(matches) == 3
    assert matches[1]["matching_entities"] == {"civil"}
    assert matches[1]["matching_articles"] == {"1234"}
    assert matches[2]["matching_entities"] == {"penal"}
    assert matches[2]["matching_articles"] == {"42"}
    assert matches[3]["matching_entities"] == {"rural"}
    assert matches[3]["matching_articles"] == {"567"}


def test_match_laws_and_articles_to_amendments():
    sample_amendments_df = pd.DataFrame(
        {
            "amdt_idx": [5, 6, 7, 8],
            "Corps amdt": [
                AttributionTextNormalizer.normalize_text(
                    "art. 32 de la loi nº 96-50 du 24 janvier 1996"
                ),
                AttributionTextNormalizer.normalize_text(
                    "article l. 321 de la loi nº 97-30 du 15 février 1997"
                ),
                AttributionTextNormalizer.normalize_text(
                    "article 56 de la loi nº 98-45 du 12 mars 1998"
                ),
                AttributionTextNormalizer.normalize_text(
                    "article 12 de la loi nº 99-60 du 20 avril 1999"
                ),
            ],
        }
    )
    laws_articles_df = pd.DataFrame(
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

    attribution_populator = AttributionPopulator(
        amendments_df=sample_amendments_df,
        attribution_mappings_when_empty=["DefaultExpert"],
        codes_articles_df=pd.DataFrame(),
        laws_articles_df=laws_articles_df,
        ordonnances_articles_df=pd.DataFrame(),
        keywords_df=pd.DataFrame(),
        name_to_email_mapping={
            "Expert1": "expert1@example.com",
            "Expert2": "expert2@example.com",
            "Expert3": "expert3@example.com",
            "DefaultExpert": "default@example.com",
        },
        ignore_non_interstitial_amdts=False,
    )

    matches = attribution_populator.match_laws_and_articles_to_amendments("Corps amdt")

    assert len(matches) == 4
    assert matches[5]["matching_entities"] == {"96-50 du 24 janvier 1996"}
    assert matches[5]["matching_articles"] == {"32"}
    assert matches[6]["matching_entities"] == {"97-30 du 15 fevrier 1997"}
    assert matches[6]["matching_articles"] == {"321"}
    assert matches[7]["matching_entities"] == {"98-45 du 12 mars 1998"}
    assert matches[7]["matching_articles"] == {"56"}
    assert matches[8]["matching_entities"] == {"99-60 du 20 avril 1999"}
    assert matches[8]["matching_articles"] == {"12"}


def test_filter_matching_entities_and_articles():
    sample_amendments_df = pd.DataFrame(
        {
            "amdt_idx": [1, 2],
            "Corps amdt": [
                AttributionTextNormalizer.normalize_text("article 1234 du code civil"),
                AttributionTextNormalizer.normalize_text("article 42 du code penal"),
            ],
        }
    )
    codes_articles_df = pd.DataFrame(
        {
            "value": [
                AttributionTextNormalizer.normalize_text("civil"),
                AttributionTextNormalizer.normalize_text("penal"),
            ],
            "Articles": ["1234", "42"],
            "Affectation (nom)": ["Expert1", "Expert2"],
        }
    )
    attribution_populator = AttributionPopulator(
        amendments_df=sample_amendments_df,
        attribution_mappings_when_empty=["DefaultExpert"],
        codes_articles_df=codes_articles_df,
        laws_articles_df=pd.DataFrame(),
        ordonnances_articles_df=pd.DataFrame(),
        keywords_df=pd.DataFrame(),
        name_to_email_mapping={
            "Expert1": "expert1@example.com",
            "DefaultExpert": "default@example.com",
        },
        ignore_non_interstitial_amdts=False,
    )

    code_matches = attribution_populator.match_codes_and_articles_to_amendments(
        "Corps amdt"
    )
    matching_rows = attribution_populator.filter_matching_entities_and_articles(
        code_matches
    )

    assert len(matching_rows) == 2
    assert "Affectation (nom)" in matching_rows.columns
    assert "amdt_idx" in matching_rows.columns


def test_aggregate_matches_by_amendment():
    sample_amendments_df = pd.DataFrame(
        {
            "amdt_idx": [1, 2],
            "Corps amdt": [
                AttributionTextNormalizer.normalize_text("article 1234 du code civil"),
                AttributionTextNormalizer.normalize_text("article 42 du code penal"),
            ],
        }
    )
    codes_articles_df = pd.DataFrame(
        {
            "value": [
                AttributionTextNormalizer.normalize_text("civil"),
                AttributionTextNormalizer.normalize_text("penal"),
            ],
            "Articles": ["1234", "42"],
            "Affectation (nom)": ["Expert1", "Expert2"],
        }
    )
    attribution_populator = AttributionPopulator(
        amendments_df=sample_amendments_df,
        attribution_mappings_when_empty=["DefaultExpert"],
        codes_articles_df=codes_articles_df,
        laws_articles_df=pd.DataFrame(),
        ordonnances_articles_df=pd.DataFrame(),
        keywords_df=pd.DataFrame(),
        name_to_email_mapping={
            "Expert1": "expert1@example.com",
            "DefaultExpert": "default@example.com",
        },
        ignore_non_interstitial_amdts=False,
    )

    matches = attribution_populator.match_codes_and_articles_to_amendments("Corps amdt")
    matching_rows = attribution_populator.filter_matching_entities_and_articles(matches)
    aggregated = attribution_populator.aggregate_matches_by_amendment(matching_rows)

    assert len(aggregated) == 2
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
def test_parallel_keyword_fuzzy_matching(mock_pool):
    mock_pool_instance = Mock()
    mock_pool_instance.starmap.return_value = [[{"keyword": "civil", "amdt_idx": "1"}]]
    mock_pool.return_value.__enter__.return_value = mock_pool_instance

    attribution_populator = AttributionPopulator(
        amendments_df=pd.DataFrame(),
        attribution_mappings_when_empty=["DefaultExpert"],
        codes_articles_df=pd.DataFrame(),
        laws_articles_df=pd.DataFrame(),
        ordonnances_articles_df=pd.DataFrame(),
        keywords_df=pd.DataFrame(),
        name_to_email_mapping={},
        ignore_non_interstitial_amdts=False,
    )

    results = attribution_populator.parallel_keyword_fuzzy_matching(
        "Corps amdt", keywords={"civil"}
    )

    assert len(results) == 1
    assert results[0]["keyword"] == "civil"


def test_calculate_ratio_of_lists():
    df = pd.DataFrame(
        {"Affectation (nom)": [["Expert1", "Expert2"], ["Expert1"], [], None]}
    )
    ratio = AttributionPopulator.calculate_ratio_of_lists(df)
    assert ratio == 0.5  # 1 list with >1 element out of 2 non-empty lists


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


def test_match_keywords_to_amendments():
    sample_amendments_df = pd.DataFrame(
        {
            "amdt_idx": [1, 2, 3],
            "Corps amdt": [
                "none",
                AttributionTextNormalizer.normalize_text("Dans le code penal"),
                "none",
            ],
            "Exposé amdt": [
                AttributionTextNormalizer.normalize_text("Exposé sur le code civil"),
                "none",
                AttributionTextNormalizer.normalize_text("Exposé sur le code rural"),
            ],
        }
    )
    keywords_df = pd.DataFrame(
        {
            "Mots clés": [
                AttributionTextNormalizer.normalize_text("civil"),
                AttributionTextNormalizer.normalize_text("penal"),
                AttributionTextNormalizer.normalize_text("rural"),
            ],
            "Affectation (nom)": ["Expert1", "Expert2", "Expert3"],
        }
    )

    attribution_populator = AttributionPopulator(
        amendments_df=sample_amendments_df,
        attribution_mappings_when_empty=["DefaultExpert"],
        codes_articles_df=pd.DataFrame(),
        laws_articles_df=pd.DataFrame(),
        ordonnances_articles_df=pd.DataFrame(),
        keywords_df=keywords_df,
        name_to_email_mapping={
            "Expert1": "expert1@example.com",
            "Expert2": "expert2@example.com",
            "Expert3": "expert3@example.com",
            "DefaultExpert": "default@example.com",
        },
        ignore_non_interstitial_amdts=False,
    )

    keyword_matches_df = attribution_populator.match_keywords_to_amendments(
        "Corps amdt"
    )

    assert len(keyword_matches_df) == 1
    assert keyword_matches_df.loc[0, "Mots clés"] == "penal"
    assert keyword_matches_df.loc[0, "Affectation (nom)"] == "Expert2"

    keyword_matches_df = attribution_populator.match_keywords_to_amendments(
        "Exposé amdt"
    )
    assert len(keyword_matches_df) == 2
    assert keyword_matches_df.loc[0, "Mots clés"] == "civil"
    assert keyword_matches_df.loc[1, "Mots clés"] == "rural"
    assert keyword_matches_df.loc[0, "Affectation (nom)"] == "Expert1"
    assert keyword_matches_df.loc[1, "Affectation (nom)"] == "Expert3"
