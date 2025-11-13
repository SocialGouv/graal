"""Matcher implementation for credit table-based matching."""

import logging
import logging.config
from typing import Any, Literal, Optional

import pandas as pd
from bs4 import BeautifulSoup, Tag

from graal.attribution.matchers.base_matcher import BaseMatcher
from graal.core.text_normalizers import TextNormalizerFactory
from graal.custom_types import (
    AttributionColumns,
    ColumnName,
    IntIndex,
    PLFProgramName,
    UserName,
)

logging.config.fileConfig("logging.conf")

TableFormat = Literal["DirectColumnFormat", "NestedHeaderFormat", "Unknown"]


class CreditTableMatcher(BaseMatcher):
    """Matches amendments based on credit table analysis."""

    def __init__(
        self,
        program_to_attribution: dict[PLFProgramName, set[UserName]],
        allowed_columns: set[AttributionColumns],
        credit_type_text: str,
    ):
        """
        Initialize the CreditTableMatcher.

        Args:
            program_to_attribution: Mapping of program names to sets of attributions
            allowed_columns: Set of column names to match against
            credit_type_text: Text used to identify credit type in tables
        """
        super().__init__(matcher_type="CREDIT_TABLE")
        self.program_to_attribution = program_to_attribution
        self.allowed_columns = allowed_columns
        self.credit_type_text = credit_type_text

    def _detect_table_format(self, table: Tag) -> TableFormat:
        """
        Detect the format of the HTML table.

        Args:
            table: BeautifulSoup table element to analyze

        Returns:
            String indicating the detected format: "DirectColumnFormat" or "NestedHeaderFormat"
        """
        # Check if the table contains the credit type text (NestedHeaderFormat format)
        if table.find(string=lambda text: text and self.credit_type_text in text):
            return "NestedHeaderFormat"

        # Check if the table has th elements (DirectColumnFormat format)
        if table.find("th"):
            return "DirectColumnFormat"

        # Default to Unknown format if we can't determine
        return "Unknown"

    def _extract_direct_column_html_table_as_df(
        self, table: Tag
    ) -> Optional[pd.DataFrame]:
        """
        Extract and parse DirectColumnFormat credit table from a BeautifulSoup table element.

        Args:
            table: BeautifulSoup Tag object representing an HTML table

        Returns:
            DataFrame containing the parsed table data or None if parsing fails
        """
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
        # Handle French-formatted numbers (e.g., '170 000 000') by removing spaces
        # and other non-digit characters before conversion, then convert to int
        for col in ["+", "-"]:
            credit_table_df[col] = (
                pd.to_numeric(
                    credit_table_df[col].astype(str).str.replace(r"\D", "", regex=True),
                    errors="coerce",
                )
                .fillna(0)
                .astype(int)
            )
        return credit_table_df

    def _extract_text_from_cell(self, cell) -> str:
        """
        Extract text from a table cell.

        Prioritizes content from the first <p> tag if present, otherwise uses cell text.
        Converts decimal numbers to integers (e.g., "5.0" -> "5").

        Args:
            cell: BeautifulSoup cell element

        Returns:
            Cleaned text content from the cell
        """
        # Extract text from first <p> tag if available, otherwise from cell directly
        p_tags = cell.find_all("p")
        text = p_tags[0].get_text().strip() if p_tags else cell.get_text().strip()

        # Convert decimal numbers to integers for cleaner display
        try:
            num = float(text)
            return str(int(num)) if num.is_integer() else text
        except ValueError:
            return text

    def _extract_program_name(self, program_cell) -> str:
        """Extract program name from a table cell."""
        progam_text = self._extract_text_from_cell(program_cell)
        attribution_normalizer = TextNormalizerFactory.get_normalizer("attribution")
        return attribution_normalizer.normalize_for_feature(progam_text)

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
        # Sometimes there are spaces (or non-numeric characters) in "+" and "-" columns which makes
        # the int casting below fail
        for col in ["+", "-"]:
            df[col] = df[col].astype(str).str.replace(r"\D", "", regex=True)
        # Convert "+" and "-" columns to integers, handling non-numeric values
        for col in ["+", "-"]:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

        return df

    def _find_credits_value_indices(self, rows: list[Tag]) -> tuple[int, int] | None:
        """
        Find the column indices for the `credit_type_text` section.

        Args:
            rows: List of table rows from BeautifulSoup

        Returns:
            Tuple of (plus_index, minus_index) or None if not found
        """
        attribution_normalizer = TextNormalizerFactory.get_normalizer("attribution")
        cells = rows[0].find_all("td")
        cells = [
            attribution_normalizer.normalize_for_feature(
                self._extract_text_from_cell(cell)
            )
            for cell in cells
        ]
        normalized_credit_text = attribution_normalizer.normalize_for_feature(
            self.credit_type_text
        )
        # Find the cell containing `credit_type_text`
        for cell_idx, cell_text in enumerate(cells):
            if normalized_credit_text in cell_text:
                return cell_idx * 2 - 1, cell_idx * 2
        return None

    def _extract_nested_header_html_table_as_df(
        self, table: Tag
    ) -> Optional[pd.DataFrame]:
        """
        Extract and parse NestedHeaderFormat credit table with 'Crédits de paiement' section.

        Args:
            table: BeautifulSoup Tag object representing an HTML table

        Returns:
            DataFrame containing the parsed table data or None if parsing fails
        """
        if table is None:
            return None

        # Find all rows
        rows = table.find_all("tr")
        if (
            len(rows) < 3
        ):  # Need at least header row, column names row, and one data row
            return None

        # Find the column indices for `credit_type_text` section dynamically
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

            # Extract "+" value from the `credit_type_text` section (e.g. "Autorisation d'engagement")
            plus_value = "0"  # Default to 0
            if credits_plus_idx < len(cells):
                plus_value = self._extract_credit_value(cells[credits_plus_idx])

            # Extract "-" value from the `credit_type_text` section (e.g. "Autorisation d'engagement")
            minus_value = "0"  # Default to 0
            if credits_minus_idx < len(cells):
                minus_value = self._extract_credit_value(cells[credits_minus_idx])

            plus_values.append(plus_value)
            minus_values.append(minus_value)

        # Create DataFrame with the same structure as the DirectColumnFormat format
        return self._create_credit_dataframe(programmes, plus_values, minus_values)

    def _normalize_programme_table(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize program names and remove totals/balance rows."""
        attribution_normalizer = TextNormalizerFactory.get_normalizer("attribution")
        df["Programmes"] = df["Programmes"].apply(
            lambda text: attribution_normalizer.normalize_for_feature(str(text))
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
            .str.contains("ligne nouvelle|nouveau programme|creer le programme")
            .any()
        ):
            return []

        possible_attributions = set()

        def add_possible_attributions(condition):
            programs = credit_table.loc[condition, "Programmes"]
            for program in programs:
                if program in self.program_to_attribution:
                    for attribution in self.program_to_attribution[program]:
                        possible_attributions.add((program, attribution))

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

    def _select_best_table(
        self, tables: list[Tag]
    ) -> tuple[Optional[Tag], TableFormat]:
        """
        Select the most appropriate table from a list of tables based on format priority.

        Args:
            tables: List of BeautifulSoup Tag objects representing HTML tables

        Returns:
            Tuple of (selected table, table format) or (None, "Unknown") if no suitable table found
        """
        selected_table = None
        selected_format: TableFormat = "Unknown"

        # Try to find a table in preferred order: NestedHeaderFormat first, then DirectColumnFormat
        for table in tables:
            table_format = self._detect_table_format(table)
            if table_format == "NestedHeaderFormat":
                selected_table = table
                selected_format = table_format
                break
            elif table_format == "DirectColumnFormat" and selected_table is None:
                selected_table = table
                selected_format = table_format

        return selected_table, selected_format

    def _extract_table_data(
        self, table: Tag, table_format: TableFormat
    ) -> Optional[pd.DataFrame]:
        """
        Extract data from a table based on its format and normalize it.

        Args:
            table: BeautifulSoup Tag object representing an HTML table
            table_format: Format of the table ("NestedHeaderFormat" or "DirectColumnFormat")

        Returns:
            Normalized DataFrame containing the parsed table data or None if extraction fails
        """
        # Extract data from the table based on its format
        if table_format == "NestedHeaderFormat":
            credit_table = self._extract_nested_header_html_table_as_df(table)
        elif table_format == "DirectColumnFormat":
            credit_table = self._extract_direct_column_html_table_as_df(table)
        else:
            return None

        if credit_table is None:
            return None

        # Normalize the table data
        credit_table = self._normalize_programme_table(credit_table)
        if credit_table.empty:
            return None

        return credit_table

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
        # Check if the column is allowed for matching
        if column_name not in self.allowed_columns:
            return []

        # Parse the HTML content
        html_content = amendment["Corps amdt original"]
        soup = BeautifulSoup(html_content, "html.parser")

        # Extract all tables
        tables = soup.find_all("table")
        if not tables:
            return []

        # Select the most appropriate table
        selected_table, selected_format = self._select_best_table(tables)
        if selected_table is None:
            logging.warning(f"No suitable table found for amdt {amendment['Num amdt']}")
            return []

        # Extract and process the table data
        credit_table = self._extract_table_data(selected_table, selected_format)
        if credit_table is None:
            logging.warning(
                f"Failed to extract credit table data for amdt {amendment['Num amdt']}"
            )
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
