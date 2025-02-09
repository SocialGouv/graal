"""Unit tests for LegalDocumentMatcher."""

import pandas as pd
import pytest

from graal.attribution.matchers.legal_document_matcher import LegalDocumentMatcher
from graal.custom_types import LegalDocumentType


@pytest.fixture
def code_documents_df():
    """Create a test codes DataFrame."""
    return pd.DataFrame(
        {
            "value": ["securite sociale", "travail"],
            "Articles": ["1", "2"],
            "Affectation (nom)": ["Social User", "Work User"],
        }
    )


@pytest.fixture
def law_documents_df():
    """Create a test laws DataFrame."""
    return pd.DataFrame(
        {
            "value": ["du 1 janvier 2024", "du 15 mars 2023"],
            "Articles": ["1", "2"],
            "Affectation (nom)": ["Law User 1", "Law User 2"],
        }
    )


@pytest.fixture
def code_matcher(code_documents_df):
    """Create a LegalDocumentMatcher instance for codes."""
    return LegalDocumentMatcher(
        document_type=LegalDocumentType.CODE,
        documents_df=code_documents_df,
        allowed_columns={"Corps amdt"},
        matcher_type="LEGAL_DOCUMENT_CODE",
    )


@pytest.fixture
def law_matcher(law_documents_df):
    """Create a LegalDocumentMatcher instance for laws."""
    return LegalDocumentMatcher(
        document_type=LegalDocumentType.LAW,
        documents_df=law_documents_df,
        allowed_columns={"Corps amdt"},
        matcher_type="LEGAL_DOCUMENT_LAW",
    )


def test_match_code(code_matcher):
    """Test matching a code reference."""
    amendment = {
        "amdt_idx": "TEST001",
        "Corps amdt": "Selon le code de la securite sociale article 1",
    }
    matches = code_matcher.match(amendment, "Corps amdt")

    assert len(matches) == 1
    assert matches[0]["amdt_idx"] == "TEST001"
    assert matches[0]["attribution"] == "Social User"
    assert matches[0]["document"] == "securite sociale"
    assert matches[0]["article"] == "1"
    assert matches[0]["document_type"] == "code"


def test_match_law(law_matcher):
    """Test matching a law reference."""
    amendment = {
        "amdt_idx": "TEST002",
        "Corps amdt": "Selon la loi du 1 janvier 2024 article 1",
    }
    matches = law_matcher.match(amendment, "Corps amdt")

    assert len(matches) == 1
    assert matches[0]["amdt_idx"] == "TEST002"
    assert matches[0]["attribution"] == "Law User 1"
    assert matches[0]["document"] == "du 1 janvier 2024"
    assert matches[0]["article"] == "1"
    assert matches[0]["document_type"] == "loi"


def test_match_multiple_articles(code_matcher):
    """Test matching multiple articles in the same code."""
    amendment = {
        "amdt_idx": "TEST003",
        "Corps amdt": "code de la securite sociale article 1 et code du travail article 2",
    }
    matches = code_matcher.match(amendment, "Corps amdt")

    assert len(matches) == 2
    articles = {match["article"] for match in matches}
    assert articles == {"1", "2"}


def test_no_document_match(code_matcher):
    """Test when no document matches."""
    amendment = {
        "amdt_idx": "TEST004",
        "Corps amdt": "code de l'environnement article 1",
    }
    matches = code_matcher.match(amendment, "Corps amdt")

    assert len(matches) == 0


def test_no_article_match(code_matcher):
    """Test when document matches but no article matches."""
    amendment = {
        "amdt_idx": "TEST005",
        "Corps amdt": "code de la securite sociale article 999",
    }
    matches = code_matcher.match(amendment, "Corps amdt")

    assert len(matches) == 0


def test_match_disallowed_column(code_matcher):
    """Test matching against a disallowed column."""
    amendment = {
        "amdt_idx": "TEST006",
        "Invalid Column": "code de la securite sociale article 1",
    }
    matches = code_matcher.match(amendment, "Invalid Column")

    assert len(matches) == 0


def test_get_attribution_comment_single_match():
    """Test generating comment for a single match."""
    matches = [
        {
            "amdt_idx": "TEST007",
            "attribution": "Test User",
            "document": "securite sociale",
            "article": "1",
            "document_type": "code",
            "column": "Corps amdt",
        }
    ]
    matcher = LegalDocumentMatcher(
        document_type=LegalDocumentType.CODE,
        documents_df=pd.DataFrame({"value": [], "Articles": []}),
        allowed_columns=set(),
        matcher_type="LEGAL_DOCUMENT_CODE",
    )
    comment = matcher.get_attribution_comment(matches)

    assert "Corps amdt" in comment
    assert "Test User" in comment
    assert "securite sociale" in comment
    assert "1" in comment


def test_get_attribution_comment_multiple_matches():
    """Test generating comment for multiple matches."""
    matches = [
        {
            "amdt_idx": "TEST008",
            "attribution": "Test User",
            "document": "securite sociale",
            "article": "1",
            "document_type": "code",
            "column": "Corps amdt",
        },
        {
            "amdt_idx": "TEST008",
            "attribution": "Test User",
            "document": "securite sociale",
            "article": "2",
            "document_type": "code",
            "column": "Corps amdt",
        },
    ]
    matcher = LegalDocumentMatcher(
        document_type=LegalDocumentType.CODE,
        documents_df=pd.DataFrame({"value": [], "Articles": []}),
        allowed_columns=set(),
        matcher_type="LEGAL_DOCUMENT_CODE",
    )
    comment = matcher.get_attribution_comment(matches)

    assert "Corps amdt" in comment
    assert "Test User" in comment
    assert "securite sociale" in comment
    assert "1, 2" in comment


def test_get_attribution_comment_no_matches():
    """Test generating comment when there are no matches."""
    matcher = LegalDocumentMatcher(
        document_type=LegalDocumentType.CODE,
        documents_df=pd.DataFrame({"value": [], "Articles": []}),
        allowed_columns=set(),
        matcher_type="LEGAL_DOCUMENT_CODE",
    )
    comment = matcher.get_attribution_comment([])

    assert comment == ""
