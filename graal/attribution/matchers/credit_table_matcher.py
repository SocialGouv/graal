"""Matcher implementation for credit table-based matching."""

import logging
import logging.config
from typing import Any

import pandas as pd
from bs4 import BeautifulSoup

from graal.attribution.matchers.base_matcher import BaseMatcher
from graal.custom_types import AttributionColumns, ColumnName, IntIndex
from graal.utils.text_utils import AttributionTextNormalizer

logging.config.fileConfig("logging.conf")


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

    def _extract_html_table_as_df(self, html_content: str) -> pd.DataFrame | None:
        """Extract and parse credit table from HTML content."""
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

    def _normalize_programme_table(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize program names and remove totals/balance rows."""
        df["Programmes"] = df["Programmes"].apply(
            lambda text: AttributionTextNormalizer.normalize_text(str(text))
        )
        df = df[~df["Programmes"].str.lower().isin(["totaux", "solde"])]
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

        # Extract and process credit table
        credit_table = self._extract_html_table_as_df(amendment["Corps amdt original"])
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
