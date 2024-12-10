import pandas as pd
import pytest

from graal.attribution.attribution_data_loader import (
    AttributionDataLoader,
)
from graal.utils.text_utils import AttributionTextNormalizer


@pytest.fixture
def excel_data():
    return {
        "Code et Article": pd.DataFrame(
            {
                "Prénom Nom": ["John Doe", "Jane Smith", "John Doe", "Bob Smith"],
                "Articles": ["Article 1", "Article 2", "Article 3", "Article 1"],
                "Type": ["code", "Code", "loi", "ordonnance"],
                "Valeur": ["Code 1", "Code 2", "Loi 1", "Ordonnance 1"],
            }
        ),
        "Mots clés": pd.DataFrame(
            {
                "Prénom Nom": ["John Doe", "John Doe", "Jane Smith"],
                "Mots clés": ["Keyword 1", "Testing with the BLA acronym", "Keyword 2"],
            }
        ),
        "Prénom Nom Mail": pd.DataFrame(
            {
                "Prénom Nom": ["John Doe", "Jane Smith"],
                "Mail": ["john.doe@example.com", "jane.smith@example.com"],
            }
        ),
        "Attribution par défaut": pd.DataFrame(
            {"Prénom Nom": ["John Doe", "Jane Smith"]}
        ),
        "Groupe avis défaut": pd.DataFrame(
            {
                "Groupe": ["Group 1", "Group 2"],
                "Avis par défaut": ["Opinion 1", "Opinion 2"],
            }
        ),
    }


def test_load_codes_and_articles(excel_data, mocker):
    mocker.patch.object(
        AttributionTextNormalizer, "normalize_text", side_effect=lambda x: x.lower()
    )
    result = AttributionDataLoader.load_codes_and_articles(excel_data)
    expected = pd.DataFrame(
        {
            "Affectation (nom)": ["John Doe", "Jane Smith"],
            "Articles": ["article 1", "article 2"],
            "Type": ["code", "code"],
            "value": ["code 1", "code 2"],
        }
    )
    pd.testing.assert_frame_equal(result, expected)


def test_load_keywords(excel_data, mocker):
    mocker.patch.object(
        AttributionTextNormalizer, "normalize_text", side_effect=lambda x: x.lower()
    )
    acronym_mapping = {"BLA": "replaced_acronym"}
    result = AttributionDataLoader.load_keywords(excel_data, acronym_mapping)
    expected = pd.DataFrame(
        {
            "Affectation (nom)": ["John Doe", "John Doe", "Jane Smith"],
            "Mots clés": [
                "keyword 1",
                "testing with the replaced_acronym acronym",
                "keyword 2",
            ],
        }
    )
    pd.testing.assert_frame_equal(result, expected)


def test_load_name_email_mappings(excel_data):
    result = AttributionDataLoader.load_name_email_mappings(excel_data)
    expected = {
        "John Doe": "john.doe@example.com",
        "Jane Smith": "jane.smith@example.com",
    }
    assert result == expected


def test_load_default_attribution_mappings(excel_data):
    result = AttributionDataLoader.load_default_attribution_mappings(excel_data)
    expected = ["John Doe", "Jane Smith"]
    assert result == expected


def test_load_group_to_default_opinion(excel_data):
    result = AttributionDataLoader.load_group_to_default_opinion(excel_data)
    expected = {"Group 1": "Opinion 1", "Group 2": "Opinion 2"}
    assert result == expected
