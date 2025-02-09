"""Unit tests for AttributionHandler."""

import logging
import logging.config

import pandas as pd
import pytest

from graal.attribution.attribution_handler import AttributionHandler
from graal.attribution.matchers.base_matcher import BaseMatcher

logging.config.fileConfig("logging.conf")


class MockMatcher(BaseMatcher):
    """Mock matcher for testing."""

    def __init__(self, matches=None, matcher_type="MOCK"):
        super().__init__(matcher_type=matcher_type)
        self.matches = matches or []

    def match(self, amendment, column_name):
        """Return predefined matches."""
        return self.matches

    def get_attribution_comment(self, matches):
        """Return a simple comment."""
        if not matches:
            return ""
        return f"Mock matcher found {len(matches)} matches"


@pytest.fixture
def default_attributions():
    """Create default attributions list."""
    return ["Default User 1", "Default User 2"]


@pytest.fixture
def user_info_mapping():
    """Create user info mapping."""
    return {
        "Test User": {"Mail": "test@example.com", "Entité Pilote": "Test Entity"},
        "Default User 1": {
            "Mail": "default1@example.com",
            "Entité Pilote": "Default Entity 1",
        },
        "Default User 2": {
            "Mail": "default2@example.com",
            "Entité Pilote": "Default Entity 2",
        },
    }


@pytest.fixture
def single_match_matcher():
    """Create a matcher that returns a single match."""
    return MockMatcher(
        matches=[
            {
                "amdt_idx": "TEST001",
                "attribution": "Test User",
                "matcher_type": "MOCK",
                "column": "Corps amdt",
            }
        ]
    )


@pytest.fixture
def multiple_match_matcher():
    """Create a matcher that returns multiple matches."""
    return MockMatcher(
        matches=[
            {
                "amdt_idx": "TEST001",
                "attribution": "Test User",
                "matcher_type": "MOCK",
                "column": "Corps amdt",
            },
            {
                "amdt_idx": "TEST001",
                "attribution": "Test User",
                "matcher_type": "MOCK",
                "column": "Exposé amdt",
            },
        ]
    )


@pytest.fixture
def no_match_matcher():
    """Create a matcher that returns no matches."""
    return MockMatcher(matches=[])


def test_process_amendments_single_match(
    single_match_matcher, default_attributions, user_info_mapping
):
    """Test processing amendments with a single match."""
    handler = AttributionHandler(
        matchers=[single_match_matcher],
        default_attributions=default_attributions,
        name_to_user_info_mapping=user_info_mapping,
    )

    amendments_df = pd.DataFrame(
        [{"amdt_idx": "TEST001", "Corps amdt": "Test text", "Commentaires": ""}]
    )
    result_df = handler.process_amendments(amendments_df)

    assert result_df.iloc[0]["Affectation (nom)"] == "Test User"
    assert result_df.iloc[0]["Affectation (email)"] == "test@example.com"
    assert result_df.iloc[0]["Entité Pilote"] == "Test Entity"
    assert "Mock matcher found 1 matches" in result_df.iloc[0]["Commentaires"]


def test_process_amendments_multiple_matches(
    multiple_match_matcher, default_attributions, user_info_mapping
):
    """Test processing amendments with multiple matches."""
    handler = AttributionHandler(
        matchers=[multiple_match_matcher],
        default_attributions=default_attributions,
        name_to_user_info_mapping=user_info_mapping,
        columns_to_match_on=["Exposé amdt"],
    )

    amendments_df = pd.DataFrame(
        [
            {
                "amdt_idx": "TEST001",
                "Corps amdt": "Test text",
                "Exposé amdt": "More text",
                "Commentaires": "",
            }
        ]
    )
    result_df = handler.process_amendments(amendments_df)

    assert result_df.iloc[0]["Affectation (nom)"] == "Test User"
    assert result_df.iloc[0]["Affectation (email)"] == "test@example.com"
    assert result_df.iloc[0]["Entité Pilote"] == "Test Entity"
    assert "Mock matcher found 2 matches" in result_df.iloc[0]["Commentaires"]


def test_process_amendments_no_matches(
    no_match_matcher, default_attributions, user_info_mapping
):
    """Test processing amendments with no matches."""
    handler = AttributionHandler(
        matchers=[no_match_matcher],
        default_attributions=default_attributions,
        name_to_user_info_mapping=user_info_mapping,
    )

    amendments_df = pd.DataFrame(
        [{"amdt_idx": "TEST001", "Corps amdt": "Test text", "Commentaires": ""}]
    )
    result_df = handler.process_amendments(amendments_df)

    # Should use a default attribution
    assert result_df.iloc[0]["Affectation (nom)"] in default_attributions
    assert result_df.iloc[0]["Affectation (email)"] in [
        "default1@example.com",
        "default2@example.com",
    ]
    assert result_df.iloc[0]["Entité Pilote"] in [
        "Default Entity 1",
        "Default Entity 2",
    ]
    assert "Attribution par défaut" in result_df.iloc[0]["Commentaires"]


def test_process_amendments_multiple_matchers(
    single_match_matcher, no_match_matcher, default_attributions, user_info_mapping
):
    """Test processing amendments with multiple matchers."""
    handler = AttributionHandler(
        matchers=[single_match_matcher, no_match_matcher],
        default_attributions=default_attributions,
        name_to_user_info_mapping=user_info_mapping,
    )

    amendments_df = pd.DataFrame(
        [{"amdt_idx": "TEST001", "Corps amdt": "Test text", "Commentaires": ""}]
    )
    result_df = handler.process_amendments(amendments_df)

    assert result_df.iloc[0]["Affectation (nom)"] == "Test User"
    assert result_df.iloc[0]["Affectation (email)"] == "test@example.com"
    assert result_df.iloc[0]["Entité Pilote"] == "Test Entity"
    assert "Mock matcher found 1 matches" in result_df.iloc[0]["Commentaires"]


def test_process_amendments_specific_columns(
    single_match_matcher, default_attributions, user_info_mapping
):
    """Test processing amendments with specific columns to match on."""
    handler = AttributionHandler(
        matchers=[single_match_matcher],
        default_attributions=default_attributions,
        name_to_user_info_mapping=user_info_mapping,
        columns_to_match_on=["Corps amdt"],
    )

    amendments_df = pd.DataFrame(
        [{"amdt_idx": "TEST001", "Corps amdt": "Test text", "Commentaires": ""}]
    )
    result_df = handler.process_amendments(amendments_df)

    assert result_df.iloc[0]["Affectation (nom)"] == "Test User"
    assert result_df.iloc[0]["Affectation (email)"] == "test@example.com"
    assert result_df.iloc[0]["Entité Pilote"] == "Test Entity"
    assert "Mock matcher found 1 matches" in result_df.iloc[0]["Commentaires"]


def test_process_amendments_empty_dataframe(
    single_match_matcher, default_attributions, user_info_mapping
):
    """Test processing an empty amendments DataFrame."""
    handler = AttributionHandler(
        matchers=[single_match_matcher],
        default_attributions=default_attributions,
        name_to_user_info_mapping=user_info_mapping,
    )

    amendments_df = pd.DataFrame(columns=["amdt_idx", "Corps amdt", "Commentaires"])
    result_df = handler.process_amendments(amendments_df)

    assert len(result_df) == 0
