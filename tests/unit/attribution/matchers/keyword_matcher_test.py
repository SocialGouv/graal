"""Unit tests for KeywordMatcher."""

import pandas as pd
import pytest

from graal.attribution.matchers.keyword_matcher import KeywordMatcher


@pytest.fixture
def keywords_df():
    """Create a test keywords DataFrame."""
    return pd.DataFrame(
        {
            "Mots clés": ["test keyword", "another test", "multi word key"],
            "Affectation (nom)": ["Test User", "Another User", "Test User"],
        }
    )


@pytest.fixture
def matcher(keywords_df):
    """Create a KeywordMatcher instance."""
    return KeywordMatcher(keywords_df, allowed_columns={"Corps amdt", "Exposé amdt"})


def test_match_single_keyword(matcher):
    """Test matching a single keyword in text."""
    amendment = {
        "amdt_idx": "TEST001",
        "Corps amdt": "This is a test keyword in some text",
    }
    matches = matcher.match(amendment, "Corps amdt")

    assert len(matches) == 1
    assert matches[0]["amdt_idx"] == "TEST001"
    assert matches[0]["attribution"] == "Test User"
    assert matches[0]["keyword"] == "test keyword"
    assert matches[0]["column"] == "Corps amdt"


def test_match_multiple_keywords(matcher):
    """Test matching multiple keywords in text."""
    amendment = {
        "amdt_idx": "TEST002",
        "Corps amdt": "Here is a test keyword and another test in the same text",
    }
    matches = matcher.match(amendment, "Corps amdt")

    assert len(matches) == 2
    attributions = {match["attribution"] for match in matches}
    assert attributions == {"Test User", "Another User"}


def test_match_multi_word_keyword(matcher):
    """Test matching keywords with multiple words."""
    amendment = {
        "amdt_idx": "TEST003",
        "Corps amdt": "Testing multi word key in text",
    }
    matches = matcher.match(amendment, "Corps amdt")

    assert len(matches) == 1
    assert matches[0]["keyword"] == "multi word key"
    assert matches[0]["attribution"] == "Test User"


def test_no_match(matcher):
    """Test when no keywords match."""
    amendment = {
        "amdt_idx": "TEST004",
        "Corps amdt": "This text contains no matching keywords",
    }
    matches = matcher.match(amendment, "Corps amdt")

    assert len(matches) == 0


def test_match_disallowed_column(matcher):
    """Test matching against a disallowed column."""
    amendment = {
        "amdt_idx": "TEST005",
        "Invalid Column": "This contains test keyword but in wrong column",
    }
    matches = matcher.match(amendment, "Invalid Column")

    assert len(matches) == 0


def test_get_attribution_comment_single_match():
    """Test generating comment for a single match."""
    matches = [
        {
            "amdt_idx": "TEST006",
            "attribution": "Test User",
            "keyword": "test keyword",
            "column": "Corps amdt",
        }
    ]
    matcher = KeywordMatcher(pd.DataFrame({"Mots clés": [None]}), allowed_columns=set())
    comment = matcher.get_attribution_comment(matches)

    assert "Corps amdt" in comment
    assert "Test User" in comment
    assert "test keyword" in comment


def test_get_attribution_comment_multiple_matches():
    """Test generating comment for multiple matches in different columns."""
    matches = [
        {
            "amdt_idx": "TEST007",
            "attribution": "Test User",
            "keyword": "test keyword",
            "column": "Corps amdt",
        },
        {
            "amdt_idx": "TEST007",
            "attribution": "Another User",
            "keyword": "another test",
            "column": "Exposé amdt",
        },
    ]
    matcher = KeywordMatcher(pd.DataFrame({"Mots clés": [None]}), allowed_columns=set())
    comment = matcher.get_attribution_comment(matches)

    assert "Corps amdt" in comment
    assert "Exposé amdt" in comment
    assert "Test User" in comment
    assert "Another User" in comment
    assert "test keyword" in comment
    assert "another test" in comment
