"""Matcher implementation for redactional amendment attribution based on article numbers."""

import logging
import logging.config
from typing import Any

import pandas as pd

from graal.attribution.matchers.base_matcher import BaseMatcher
from graal.custom_types import AttributionMatcherType, ColumnName

logging.config.fileConfig("logging.conf")
logger = logging.getLogger(__name__)


class RedactionalAmendmentMatcher(BaseMatcher):
    """Matches redactional amendments based on article numbers using the subsidiary table."""

    def __init__(
        self,
        subsidiary_df: pd.DataFrame,
        allowed_columns: set[ColumnName],
        matcher_type: AttributionMatcherType = "REDACTIONAL_AMENDMENT",
    ):
        """
        Initialize the RedactionalAmendmentMatcher.

        Args:
            subsidiary_df: DataFrame containing subsidiary table data with columns:
                        - Numéro article: article number
                        - Affectation (nom): attribution name
                        - Entité Pilote: entity information
            allowed_columns: Set of column names to match against
            matcher_type: Type of matcher for identification
        """
        super().__init__(matcher_type=matcher_type)
        self.subsidiary_df = subsidiary_df
        self.allowed_columns = allowed_columns or {"Exposé amdt"}

        # Create a mapping from article number to attribution for faster lookup
        self.article_to_attribution = {}
        if not subsidiary_df.empty:
            for _, row in subsidiary_df.iterrows():
                article_num = str(row["Numéro article"]).strip().lower()
                attribution = row["Affectation (nom)"]
                if article_num and attribution:
                    self.article_to_attribution[article_num] = attribution

    def match(
        self, amendment: dict[str, Any], column_name: str
    ) -> list[dict[str, str]]:
        """
        Match redactional amendments based on article numbers.

        Args:
            amendment: Dictionary containing amendment data
            column_name: Name of the column to match against

        Returns:
            List of dictionaries containing match information
        """
        if column_name not in self.allowed_columns:
            return []

        # Check if this is a redactional amendment
        if not amendment.get("is_redactional", False):
            return []

        # Extract article number from the amendment
        article_num = amendment.get("Num article", "").strip().lower()
        if not article_num:
            logger.warning(
                f"Redactional amendment {amendment.get('amdt_idx', 'unknown')} "
                f"has no article number."
            )
            return []

        # Look up attribution in subsidiary table
        attribution = self.article_to_attribution.get(article_num)
        if not attribution:
            logger.warning(
                f"Article number '{article_num}' not found in subsidiary table "
                f"for redactional amendment {amendment.get('amdt_idx', 'unknown')}. "
                f"Will fall back to default attribution."
            )
            return []

        return [
            {
                "amdt_idx": amendment["amdt_idx"],
                "attribution": attribution,
                "article_number": article_num,
                "matcher": "RedactionalAmendmentMatcher",
                "matcher_type": self.matcher_type,
                "column": column_name,
            }
        ]

    def get_attribution_comment(self, matches: list[dict[str, str]]) -> str:
        """
        Generate a comment explaining the redactional amendment attribution.

        Args:
            matches: List of match dictionaries from the match() method

        Returns:
            String containing the attribution comment
        """
        if not matches:
            return ""

        columns = {match["column"] for match in matches}
        comments = []

        for column in sorted(columns):
            comments.append(
                f"Affectations par amendement rédactionnel dans '{column}' :"
            )
            column_matches = [m for m in matches if m["column"] == column]
            attributions = {match["attribution"] for match in column_matches}

            for attribution in sorted(attributions):
                article_numbers = sorted(
                    {
                        m["article_number"]
                        for m in column_matches
                        if m["attribution"] == attribution
                    }
                )
                comments.append(f"{attribution} : article {', '.join(article_numbers)}")

        return "\n".join(comments)
