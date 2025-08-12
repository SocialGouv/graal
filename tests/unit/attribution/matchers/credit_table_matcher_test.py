"""Unit tests for CreditTableMatcher."""

import logging
import logging.config

import pandas as pd
import pytest
from bs4 import BeautifulSoup

from graal.attribution.matchers.credit_table_matcher import CreditTableMatcher

logging.config.fileConfig("logging.conf")


@pytest.fixture
def program_mapping():
    """Create a test program to attribution mapping."""
    return {
        "programme 123 sante publique": {"Alice"},
        "programme 456 education nationale": {"Bob"},
        "programme 789 recherche": {"Charles"},
    }


@pytest.fixture
def matcher(program_mapping):
    """Create a CreditTableMatcher instance."""
    return CreditTableMatcher(
        program_mapping,
        allowed_columns={"Corps amdt original"},
        credit_type_text="Crédits de paiement",
    )


@pytest.fixture
def direct_column_credit_table():
    """Create a DirectColumnFormat HTML credit table."""
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


def test_extract_direct_column_html_table_as_df(matcher, direct_column_credit_table):
    """Test extracting DataFrame from HTML table."""
    # Parse the HTML string to get a BeautifulSoup Tag object
    soup = BeautifulSoup(direct_column_credit_table, "html.parser")
    table = soup.find("table")

    df = matcher._extract_direct_column_html_table_as_df(table)

    assert isinstance(df, pd.DataFrame)
    assert list(df.columns) == ["Programmes", "+", "-"]
    assert len(df) == 2
    assert df["+"].dtype == "int"
    assert df["-"].dtype == "int"


def test_extract_direct_column_html_table_as_df_no_table(matcher):
    """Test handling HTML content with no table."""
    df = matcher._extract_direct_column_html_table_as_df(None)
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
    assert matches[0]["attribution"] == "Alice"
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
    assert matches[0]["attribution"] == "Alice"
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
            "attribution": "Alice",
            "program": "programme 123 sante publique",
            "matcher": "CreditTableMatcher",
            "matcher_type": "CREDIT_TABLE",
            "column": "Corps amdt original",
        }
    ]
    matcher = CreditTableMatcher(
        {}, allowed_columns=set(), credit_type_text="Crédits de paiement"
    )
    comment = matcher.get_attribution_comment(matches)

    assert "Affectations par tableau de crédits" in comment
    assert "Alice" in comment
    assert "programme 123 sante publique" in comment


def test_get_attribution_comment_multiple_matches():
    """Test generating comment for multiple matches."""
    matches = [
        {
            "amdt_idx": "TEST006",
            "attribution": "Alice",
            "program": "programme 123 sante publique",
            "matcher": "CreditTableMatcher",
            "matcher_type": "CREDIT_TABLE",
            "column": "Corps amdt original",
        },
        {
            "amdt_idx": "TEST006",
            "attribution": "Bob",
            "program": "programme 456 education nationale",
            "matcher": "CreditTableMatcher",
            "matcher_type": "CREDIT_TABLE",
            "column": "Corps amdt original",
        },
    ]
    matcher = CreditTableMatcher(
        {}, allowed_columns=set(), credit_type_text="Crédits de paiement"
    )
    comment = matcher.get_attribution_comment(matches)

    assert "Affectations par tableau de crédits" in comment
    assert "Alice" in comment
    assert "Bob" in comment
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
    amendment = {
        "amdt_idx": "TEST007",
        "Corps amdt original": html,
        "Num amdt": "TEST007",
    }

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
    assert attributions == {"Alice", "Bob"}
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
    assert attributions == {"Alice", "Bob", "Charles"}
    programs = {match["program"] for match in matches}
    assert programs == {
        "programme 123 sante publique",
        "programme 456 education nationale",
        "programme 789 recherche",
    }


@pytest.fixture
def nested_header_credit_table():
    """Create a NestedHeaderFormat HTML credit table with 'Crédits de paiement' section."""
    return """
    <table>
        <tbody>
            <tr>
                <td>
                    <p><b>Programmes</b>
                    </p>
                </td>
                <td colspan="2">
                    <p><b>Autorisations d'engagement</b>
                    </p>
                </td>
                <td colspan="2">
                    <p><b>Crédits de paiement</b>
                    </p>
                </td>
            </tr>
            <tr>
                <td>
                    <p> </p>
                </td>
                <td>
                    <p>+</p>
                </td>
                <td>
                    <p>-</p>
                </td>
                <td>
                    <p>+</p>
                </td>
                <td>
                    <p>-</p>
                </td>
            </tr>
            <tr>
                <td>
                    <p><b>Soutien aux prestations de l'aviation civile </b>
                    </p>
                    <p>dont titre 2</p>
                </td>
                <td>
                    <p> </p>
                </td>
                <td>
                    <p>9 399 999</p>
                    <p><i>4 308 111</i>
                    </p>
                </td>
                <td>
                    <p>9 397 611</p>
                    <p><i>4 308 569</i>
                    </p>
                </td>
                <td>
                    <p> </p>
                </td>
            </tr>
            <tr>
                <td>
                    <p><b>Navigation aérienne </b>
                    </p>
                </td>
                <td>
                    <p> </p>
                </td>
                <td>
                    <p>10 000 000</p>
                </td>
                <td>
                    <p> </p>
                </td>
                <td>
                    <p>5 000 000</p>
                </td>
            </tr>
            <tr>
                <td>
                    <p><b>Transports aériens, surveillance et certification </b>
                    </p>
                </td>
                <td>
                    <p> </p>
                </td>
                <td>
                    <p>4 200 000</p>
                </td>
                <td>
                    <p> </p>
                </td>
                <td>
                    <p>4 200 000</p>
                </td>
            </tr>
            <tr>
                <td>
                    <p><b>TOTAL</b>
                    </p>
                </td>
                <td>
                    <p><b> </b>
                    </p>
                </td>
                <td>
                    <p><b>23 597 611</b>
                    </p>
                </td>
                <td>
                    <p><b> </b>
                    </p>
                </td>
                <td>
                    <p><b>18 597 611</b>
                    </p>
                </td>
            </tr>
            <tr>
                <td>
                    <p><b>SOLDE</b>
                    </p>
                </td>
                <td colspan="2">
                    <p><b>- 23 597 611</b>
                    </p>
                </td>
                <td colspan="2">
                    <p><b>- 18 597 611</b>
                    </p>
                </td>
            </tr>
        </tbody>
    </table>
    """


def test_detect_table_format(
    matcher, direct_column_credit_table, nested_header_credit_table
):
    """Test detection of table format."""
    # Test DirectColumnFormat format detection
    soup = BeautifulSoup(direct_column_credit_table, "html.parser")
    assert matcher._detect_table_format(soup) == "DirectColumnFormat"

    # Test NestedHeaderFormat format detection
    soup = BeautifulSoup(nested_header_credit_table, "html.parser")
    assert matcher._detect_table_format(soup) == "NestedHeaderFormat"


def test_extract_nested_header_html_table(matcher, nested_header_credit_table):
    """Test extracting DataFrame from NestedHeaderFormat HTML table."""
    # Parse the HTML string to get a BeautifulSoup Tag object
    soup = BeautifulSoup(nested_header_credit_table, "html.parser")
    table = soup.find("table")

    df = matcher._extract_nested_header_html_table_as_df(table)

    assert isinstance(df, pd.DataFrame)
    assert list(df.columns) == ["Programmes", "+", "-"]
    assert len(df) == 3  # 3 program rows (excluding TOTAL and SOLDE)
    assert df["+"].values.tolist() == [9397611, 0, 0]
    assert df["-"].values.tolist() == [0, 5000000, 4200000]

    # Check that the correct values were extracted
    assert "soutien aux prestation de l'aviation civile" in df["Programmes"].values[0]


@pytest.fixture
def unknown_format_table():
    """Create a table with unknown format."""
    return """
    <table>
        <tr>
            <td>This is not a credit table</td>
            <td>It has no proper headers</td>
        </tr>
        <tr>
            <td>Just some random data</td>
            <td>Nothing useful here</td>
        </tr>
    </table>
    """


def test_match_multiple_tables_prioritize_nested_header(
    nested_header_credit_table, direct_column_credit_table
):
    """Test that NestedHeaderFormat table is prioritized when multiple tables exist."""
    # Create HTML with both table formats, with NestedHeaderFormat second
    html = f"""
    <div>
        {direct_column_credit_table}
        {nested_header_credit_table}
    </div>
    """
    amendment = {
        "amdt_idx": "TEST011",
        "Corps amdt original": html,
        "Num amdt": "TEST011",
    }

    # Create a custom program mapping that includes aviation programs
    aviation_matcher = CreditTableMatcher(
        {
            "soutien aux prestation de l'aviation civile": {"JCVD"},
            "navigation aerienne": {"Patrick"},
            "transports aeriens surveillance et certification": {"Jean-Noël"},
        },
        allowed_columns={"Corps amdt original"},
        credit_type_text="Crédits de paiement",
    )

    matches = aviation_matcher.match(amendment, "Corps amdt original")
    assert len(matches) > 0
    attributions = {match["attribution"] for match in matches}
    assert "JCVD" in attributions


def test_match_multiple_tables_direct_column_only(
    matcher, direct_column_credit_table, unknown_format_table
):
    """Test that DirectColumnFormat table is selected when no NestedHeaderFormat exists."""
    # Create HTML with DirectColumnFormat and unknown format tables
    html = f"""
    <div>
        {unknown_format_table}
        {direct_column_credit_table}
    </div>
    """
    amendment = {
        "amdt_idx": "TEST012",
        "Corps amdt original": html,
        "Num amdt": "TEST012",
    }

    # The matcher should select the DirectColumnFormat table
    matches = matcher.match(amendment, "Corps amdt original")

    # Verify that matches come from the DirectColumnFormat table
    assert len(matches) == 2
    attributions = {match["attribution"] for match in matches}
    assert attributions == {"Alice", "Bob"}
    programs = {match["program"] for match in matches}
    assert programs == {
        "programme 123 sante publique",
        "programme 456 education nationale",
    }


def test_match_multiple_tables_no_valid_format(matcher, unknown_format_table):
    """Test that no table is selected when none have a valid format."""
    # Create HTML with multiple unknown format tables
    html = f"""
    <div>
        {unknown_format_table}
        {unknown_format_table}
    </div>
    """
    amendment = {
        "amdt_idx": "TEST013",
        "Corps amdt original": html,
        "Num amdt": "TEST013",
    }

    # The matcher should not select any table
    matches = matcher.match(amendment, "Corps amdt original")
    assert len(matches) == 0


def test_match_multiple_nested_header_tables(matcher, nested_header_credit_table):
    """Test that the first NestedHeaderFormat table is selected when multiple exist."""
    # Create a modified version of the nested header table
    modified_nested_table = nested_header_credit_table.replace(
        "Soutien aux prestations de l'aviation civile", "Programme 123 Sante Publique"
    )

    # Create HTML with two NestedHeaderFormat tables
    html = f"""
    <div>
        {modified_nested_table}
        {nested_header_credit_table}
    </div>
    """
    amendment = {
        "amdt_idx": "TEST014",
        "Corps amdt original": html,
        "Num amdt": "TEST014",
    }

    # The matcher should select the first NestedHeaderFormat table
    matches = matcher.match(amendment, "Corps amdt original")

    # Check that we got matches from the first table (with the modified program name)
    programs = {match["program"] for match in matches}
    assert any("sante" in program.lower() for program in programs)
