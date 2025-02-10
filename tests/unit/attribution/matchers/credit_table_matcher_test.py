"""Unit tests for CreditTableMatcher."""

import pandas as pd
import pytest

from graal.attribution.matchers.credit_table_matcher import CreditTableMatcher


@pytest.fixture
def program_mapping():
    """Create a test program to attribution mapping."""
    return {
        "programme 123 sante publique": "Health",
        "programme 456 education nationale": "Education",
        "programme 789 recherche": "Research",
    }


@pytest.fixture
def matcher(program_mapping):
    """Create a CreditTableMatcher instance."""
    return CreditTableMatcher(program_mapping, allowed_columns={"Corps amdt original"})


@pytest.fixture
def basic_credit_table():
    """Create a basic HTML credit table."""
    return """
    <table>
        <tr>
            <th>Programmes</th>
            <th>+</th>
            <th>-</th>
        </tr>
        <tr>
            <td>Programme 123 Sante Publique</td>
            <td>0</td>
            <td>100</td>
        </tr>
        <tr>
            <td>Programme 456 Education Nationale</td>
            <td>0</td>
            <td>100</td>
        </tr>
    </table>
    """


def test_extract_html_table(matcher, basic_credit_table):
    """Test extracting DataFrame from HTML table."""
    df = matcher._extract_html_table_as_df(basic_credit_table)

    assert isinstance(df, pd.DataFrame)
    assert list(df.columns) == ["Programmes", "+", "-"]
    assert len(df) == 2
    assert df["+"].dtype == "int"
    assert df["-"].dtype == "int"


def test_extract_html_table_no_table(matcher):
    """Test handling HTML content with no table."""
    df = matcher._extract_html_table_as_df("<div>No table here</div>")
    assert df is None


def test_normalize_programme_table(matcher):
    """Test normalizing program names and filtering totals."""
    df = pd.DataFrame(
        {
            "Programmes": [
                "Programme 123 Santé Publique",
                "Totaux",
                "SOLDE",
                "Programme 456",
            ],
            "+": [100, 200, 0, 50],
            "-": [0, 100, 100, 0],
        }
    )

    normalized_df = matcher._normalize_programme_table(df)

    assert len(normalized_df) == 2  # Totaux and SOLDE should be removed
    assert "programme 123 sante publique" in normalized_df["Programmes"].values
    assert "programme 456" in normalized_df["Programmes"].values


def test_match_new_program_line(matcher):
    """Test handling tables with new program lines."""
    html = """
    <table>
        <tr>
            <th>Programmes</th>
            <th>+</th>
            <th>-</th>
        </tr>
        <tr>
            <td>Ligne nouvelle</td>
            <td>100</td>
            <td>0</td>
        </tr>
    </table>
    """
    amendment = {"amdt_idx": "TEST001", "Corps amdt original": html}

    matches = matcher.match(amendment, "Corps amdt original")
    assert len(matches) == 0


def test_match_credit_reduction(matcher):
    """Test matching when credits are only reduced."""
    html = """
    <table>
        <tr>
            <th>Programmes</th>
            <th>+</th>
            <th>-</th>
        </tr>
        <tr>
            <td>Programme 123 Sante Publique</td>
            <td>0</td>
            <td>100</td>
        </tr>
    </table>
    """
    amendment = {"amdt_idx": "TEST002", "Corps amdt original": html}

    matches = matcher.match(amendment, "Corps amdt original")
    assert len(matches) == 1
    assert matches[0]["attribution"] == "Health"
    assert matches[0]["program"] == "programme 123 sante publique"


def test_match_credit_transfer(matcher):
    """Test matching when credits are both added and reduced."""
    html = """
    <table>
        <tr>
            <th>Programmes</th>
            <th>+</th>
            <th>-</th>
        </tr>
        <tr>
            <td>Programme 123 Sante Publique</td>
            <td>100</td>
            <td>50</td>
        </tr>
        <tr>
            <td>Programme 456 Education Nationale</td>
            <td>0</td>
            <td>100</td>
        </tr>
    </table>
    """
    amendment = {"amdt_idx": "TEST003", "Corps amdt original": html}

    matches = matcher.match(amendment, "Corps amdt original")
    assert len(matches) == 1
    assert matches[0]["attribution"] == "Health"
    assert matches[0]["program"] == "programme 123 sante publique"


def test_match_disallowed_column(matcher):
    """Test matching against a disallowed column."""
    amendment = {
        "amdt_idx": "TEST004",
        "Corps amdt original": "<table><tr><td>Some content</td></tr></table>",
    }
    matches = matcher.match(amendment, "Exposé amdt")
    assert len(matches) == 0


def test_get_attribution_comment_single_match():
    """Test generating comment for a single match."""
    matches = [
        {
            "amdt_idx": "TEST005",
            "attribution": "Health",
            "program": "programme 123 sante publique",
            "matcher": "CreditTableMatcher",
            "matcher_type": "CREDIT_TABLE",
            "column": "Corps amdt original",
        }
    ]
    matcher = CreditTableMatcher({}, allowed_columns=set())
    comment = matcher.get_attribution_comment(matches)

    assert "Affectations par tableau de crédits" in comment
    assert "Health" in comment
    assert "programme 123 sante publique" in comment


def test_get_attribution_comment_multiple_matches():
    """Test generating comment for multiple matches."""
    matches = [
        {
            "amdt_idx": "TEST006",
            "attribution": "Health",
            "program": "programme 123 sante publique",
            "matcher": "CreditTableMatcher",
            "matcher_type": "CREDIT_TABLE",
            "column": "Corps amdt original",
        },
        {
            "amdt_idx": "TEST006",
            "attribution": "Education",
            "program": "programme 456 education nationale",
            "matcher": "CreditTableMatcher",
            "matcher_type": "CREDIT_TABLE",
            "column": "Corps amdt original",
        },
    ]
    matcher = CreditTableMatcher({}, allowed_columns=set())
    comment = matcher.get_attribution_comment(matches)

    assert "Affectations par tableau de crédits" in comment
    assert "Health" in comment
    assert "Education" in comment
    assert "programme 123 sante publique" in comment
    assert "programme 456 education nationale" in comment


def test_match_empty_table(matcher):
    """Test handling empty credit table."""
    html = """
    <table>
        <tr>
            <th>Programmes</th>
            <th>+</th>
            <th>-</th>
        </tr>
    </table>
    """
    amendment = {"amdt_idx": "TEST007", "Corps amdt original": html}

    matches = matcher.match(amendment, "Corps amdt original")
    assert len(matches) == 0


def test_match_invalid_html(matcher):
    """Test handling invalid HTML content."""
    amendment = {
        "amdt_idx": "TEST008",
        "Corps amdt original": "<invalid>html</invalid>",
    }

    matches = matcher.match(amendment, "Corps amdt original")
    assert len(matches) == 0


def test_match_credit_reduction_only(matcher):
    """Test matching when only - column has positive values."""
    html = """
    <table>
        <tr>
            <th>Programmes</th>
            <th>+</th>
            <th>-</th>
        </tr>
        <tr>
            <td>Programme 123 Sante Publique</td>
            <td>0</td>
            <td>100</td>
        </tr>
        <tr>
            <td>Programme 456 Education Nationale</td>
            <td>0</td>
            <td>50</td>
        </tr>
    </table>
    """
    amendment = {"amdt_idx": "TEST010", "Corps amdt original": html}

    matches = matcher.match(amendment, "Corps amdt original")
    assert len(matches) == 2
    attributions = {match["attribution"] for match in matches}
    assert attributions == {"Health", "Education"}
    programs = {match["program"] for match in matches}
    assert programs == {
        "programme 123 sante publique",
        "programme 456 education nationale",
    }


def test_match_credit_both_columns(matcher):
    """Test matching when both + and - columns have positive values."""
    html = """
    <table>
        <tr>
            <th>Programmes</th>
            <th>+</th>
            <th>-</th>
        </tr>
        <tr>
            <td>Programme 123 Sante Publique</td>
            <td>100</td>
            <td>50</td>
        </tr>
        <tr>
            <td>Programme 456 Education Nationale</td>
            <td>50</td>
            <td>100</td>
        </tr>
        <tr>
            <td>Programme 789 Recherche</td>
            <td>100</td>
            <td>50</td>
        </tr>
    </table>
    """
    amendment = {"amdt_idx": "TEST009", "Corps amdt original": html}

    matches = matcher.match(amendment, "Corps amdt original")
    assert len(matches) == 3
    attributions = {match["attribution"] for match in matches}
    assert attributions == {"Health", "Education", "Research"}
    programs = {match["program"] for match in matches}
    assert programs == {
        "programme 123 sante publique",
        "programme 456 education nationale",
        "programme 789 recherche",
    }
