"""Matcher implementation for credit table-based matching."""

import logging
import logging.config
from typing import Any, Literal

import pandas as pd
from bs4 import BeautifulSoup

from graal.attribution.matchers.base_matcher import BaseMatcher
from graal.custom_types import AttributionColumns, ColumnName, IntIndex
from graal.utils.text_utils import AttributionTextNormalizer

logging.config.fileConfig("logging.conf")

TableFormat = Literal["standard", "complex"]


class CreditTableMatcher(BaseMatcher):
    """Matches amendments based on credit table analysis."""

    def __init__(
        self,
        program_to_attribution: dict[str, str],
        allowed_columns: set[AttributionColumns],
    ):
        """
        Initialize the CreditTableMatcher.

        Args:
            program_to_attribution: Mapping of program names to attributions
            allowed_columns: Set of column names to match against
        """
        super().__init__(matcher_type="CREDIT_TABLE")
        self.program_to_attribution = program_to_attribution
        self.allowed_columns = allowed_columns

    def _detect_table_format(self, soup: BeautifulSoup) -> TableFormat:
        """
        Detect the format of the HTML table.

        Args:
            soup: BeautifulSoup object containing the parsed HTML

        Returns:
            String indicating the detected format: "standard" or "complex"
        """
        # Check if the table contains "Crédits de paiement" text (complex format)
        if soup.find(string=lambda text: text and "Crédits de paiement" in text):
            return "complex"

        # Check if the table has th elements (standard format)
        if soup.find("th"):
            return "standard"

        # Default to standard format if we can't determine
        return "standard"

    def _extract_html_table_as_df(self, html_content: str) -> pd.DataFrame | None:
        """Extract and parse standard credit table from HTML content."""
        # Parse the HTML content
        soup = BeautifulSoup(html_content, "html.parser")

        # Extract the table
        table = soup.find("table")
        if table is None:
            return None

        # Extract the table header
        header = [th.text.strip() for th in table.find_all("th")]

        # Extract rows from the table
        rows = table.find_all("tr")

        table_rows = []
        for row in rows[1:]:  # Skip header row
            cols = row.find_all("td")
            cols = [ele.text.strip() for ele in cols]
            table_rows.append(cols)

        credit_table_df = pd.DataFrame(table_rows, columns=header)
        credit_table_df["+"] = credit_table_df["+"].fillna(0)
        credit_table_df["-"] = credit_table_df["-"].fillna(0)
        credit_table_df["+"] = credit_table_df["+"].astype(int)
        credit_table_df["-"] = credit_table_df["-"].astype(int)
        return credit_table_df

    def _extract_text_from_cell(self, cell) -> str:
        """Extract text from a table cell, returning content of first <p> tag if it exists."""
        p_tags = cell.find_all("p")
        if p_tags:
            return p_tags[0].get_text().strip()
        return cell.get_text().strip()

    def _extract_program_name(self, program_cell) -> str:
        """Extract program name from a table cell."""
        progam_text = self._extract_text_from_cell(program_cell)
        return AttributionTextNormalizer.normalize_text(progam_text)

    def _extract_credit_value(self, cell) -> str:
        """Extract credit value from a table cell."""
        try:
            text = self._extract_text_from_cell(cell)
            if text and text != " ":
                return text.replace(" ", "")
            return "0"
        except Exception as e:
            logging.warning(f"Error extracting credit value: {e}")
            return "0"

    def _create_credit_dataframe(
        self, programmes, plus_values, minus_values
    ) -> pd.DataFrame:
        """Create a DataFrame from extracted credit data and convert values to integers."""
        data = {"Programmes": programmes, "+": plus_values, "-": minus_values}
        df = pd.DataFrame(data)

        # Convert "+" and "-" columns to integers, handling non-numeric values
        for col in ["+", "-"]:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

        return df

    def _find_credits_value_indices(self, rows) -> tuple[int, int] | None:
        """
        Find the column indices for the "Crédits de paiement" section.

        Args:
            rows: List of table rows from BeautifulSoup

        Returns:
            Tuple of (plus_index, minus_index) or None if not found
        """
        cells = rows[0].find_all("td")
        cells = [
            AttributionTextNormalizer.normalize_text(self._extract_text_from_cell(cell))
            for cell in cells
        ]
        normalized_credit_text = AttributionTextNormalizer.normalize_text(
            "Crédits de paiement"
        )
        # Find the cell containing "Crédits de paiement"
        for cell_idx, cell_text in enumerate(cells):
            if normalized_credit_text in cell_text:
                return cell_idx * 2 - 1, cell_idx * 2
        return None

    def _extract_complex_html_table_as_df(
        self, html_content: str
    ) -> pd.DataFrame | None:
        """Extract and parse complex credit table with 'Crédits de paiement' section."""
        soup = BeautifulSoup(html_content, "html.parser")

        table = soup.find("table")
        if table is None:
            return None

        # Find all rows
        rows = table.find_all("tr")
        if (
            len(rows) < 3
        ):  # Need at least header row, column names row, and one data row
            return None

        # Find the column indices for "Crédits de paiement" section dynamically
        indices = self._find_credits_value_indices(rows)

        if indices is None:
            return None
        credits_plus_idx, credits_minus_idx = indices

        # Extract program names and credit values
        programmes = []
        plus_values = []
        minus_values = []

        # Process data rows, skipping header rows and TOTAL/SOLDE rows
        for row in rows[2:]:  # Skip header rows
            cells = row.find_all("td")

            if len(cells) <= 1:
                continue

            # Get the program name from the first column
            program_text = self._extract_program_name(cells[0])

            # Skip rows that don't have a proper program name or are TOTAL/SOLDE rows
            if not program_text or program_text.lower() in ["total", "solde"]:
                continue

            programmes.append(program_text)

            # Extract "+" value from the Crédits de paiement section
            plus_value = "0"  # Default to 0
            if len(cells) > credits_plus_idx:
                plus_value = self._extract_credit_value(cells[credits_plus_idx])

            # Extract "-" value from the Crédits de paiement section
            minus_value = "0"  # Default to 0
            if len(cells) > credits_minus_idx:
                minus_value = self._extract_credit_value(cells[credits_minus_idx])

            plus_values.append(plus_value)
            minus_values.append(minus_value)

        # Create DataFrame with the same structure as the standard format
        return self._create_credit_dataframe(programmes, plus_values, minus_values)

    def _normalize_programme_table(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize program names and remove totals/balance rows."""
        df["Programmes"] = df["Programmes"].apply(
            lambda text: AttributionTextNormalizer.normalize_text(str(text))
        )
        df = df[~df["Programmes"].str.lower().isin(["total", "solde"])]
        return df

    def _get_attribution_for_credit_table(  # noqa: C901
        self,
        credit_table: pd.DataFrame,
        amdt_idx: IntIndex,
        column_name: ColumnName,
    ) -> list[dict[str, Any]]:
        """Determine attributions based on credit table analysis."""
        # Case 1: If there is a new line or new program, skip as keyword matching on Exposé amdt will be used instead
        if (
            credit_table["Programmes"]
            .str.contains("ligne nouvelle|nouveau programme")
            .any()
        ):
            return []

        possible_attributions = set()

        def add_possible_attributions(condition):
            programs = credit_table.loc[condition, "Programmes"]
            for program in programs:
                if program in self.program_to_attribution:
                    possible_attributions.add(
                        (program, self.program_to_attribution[program])
                    )

        # Case 2: All zeros in + column, some positive in - column
        if (credit_table["+"] == 0).all() and (credit_table["-"] > 0).any():
            add_possible_attributions(credit_table["-"] > 0)
        # Case 3: Positive values in both + and - columns
        if (credit_table["-"] > 0).any():
            add_possible_attributions(credit_table["+"] > 0)

        return [
            {
                "amdt_idx": amdt_idx,
                "attribution": attribution,
                "program": program,
                "matcher": "CreditTableMatcher",
                "matcher_type": self.matcher_type,
                "column": column_name,
            }
            for program, attribution in possible_attributions
        ]

    def match(
        self, amendment: dict[str, Any], column_name: str
    ) -> list[dict[str, str]]:
        """
        Match credit tables against amendment text.

        Args:
            amendment: Dictionary containing amendment data
            column_name: Name of the column to match against

        Returns:
            List of dictionaries containing match information
        """
        if column_name not in self.allowed_columns:
            return []

        # Parse the HTML content
        html_content = amendment["Corps amdt original"]
        soup = BeautifulSoup(html_content, "html.parser")

        # Extract the table
        table = soup.find("table")
        if table is None:
            return []

        # Detect table format and extract accordingly
        table_format = self._detect_table_format(soup)

        if table_format == "complex":
            credit_table = self._extract_complex_html_table_as_df(html_content)
        else:
            credit_table = self._extract_html_table_as_df(html_content)

        if credit_table is None:
            return []

        credit_table = self._normalize_programme_table(credit_table)
        if credit_table.empty:
            return []

        # Get attributions based on credit table analysis
        attributions = self._get_attribution_for_credit_table(
            credit_table, amendment["amdt_idx"], column_name
        )

        return attributions

    def get_attribution_comment(self, matches: list[dict[str, str]]) -> str:
        """
        Generate a comment explaining the credit table-based attribution.

        Args:
            matches: List of match dictionaries from the match() method

        Returns:
            String containing the attribution comment
        """
        if not matches:
            return ""

        attributions = {match["attribution"] for match in matches}

        comments = ["Affectations par tableau de crédits :"]
        for attribution in sorted(attributions):
            attribution_programs = sorted(
                {m["program"] for m in matches if m["attribution"] == attribution}
            )
            comments.append(f"{attribution} : [{', '.join(attribution_programs)}]")

        return "\n".join(comments)
