"""Matcher implementation for keyword-based matching."""

import re
from collections import Counter
from typing import Any, Dict, List

import pandas as pd

from graal.attribution.matchers.base_matcher import BaseMatcher
from graal.custom_types import AttributionColumns


class KeywordMatcher(BaseMatcher):
    """Matches amendments based on keyword presence."""

    def __init__(
        self,
        keywords_df: pd.DataFrame,
        allowed_columns: set[AttributionColumns],
    ):
        """
        Initialize the KeywordMatcher.

        Args:
            keywords_df: DataFrame containing keywords and their attributions
        """
        super().__init__(matcher_type="KEYWORD")
        self.allowed_columns = allowed_columns
        self.keywords_df = keywords_df
        self.keywords = set(keywords_df["Mots clés"].dropna())
        self.split_pattern = r"[\s\n\r\t\f'.,;:!?\"(){}<>-\[\]]+"

    def match(
        self, amendment: Dict[str, Any], column_name: str
    ) -> List[Dict[str, str]]:
        """
        Match keywords against amendment text.

        Args:
            amendment: Dictionary containing amendment data
            column_name: Name of the column to match against

        Returns:
            List of dictionaries containing match information
        """
        if column_name not in self.allowed_columns:
            return []

        amendment_text = amendment[column_name]
        amdt_words = [
            word
            for word in re.split(self.split_pattern, amendment_text)
            if len(word.strip()) > 0
        ]

        results = []
        for keyword in self.keywords:
            keyword_words = [
                word
                for word in re.split(self.split_pattern, keyword)
                if len(word.strip()) > 0
            ]

            if not keyword_words:
                continue

            # Get attribution(s) for this keyword once.
            attributions = self.keywords_df[self.keywords_df["Mots clés"] == keyword][
                "Affectation (nom)"
            ].tolist()
            if not attributions:
                continue

            # Count every occurrence of the full keyword phrase, including overlapping.
            phrase_len = len(keyword_words)
            for start_idx in range(0, max(0, len(amdt_words) - phrase_len + 1)):
                end_idx = start_idx + phrase_len
                if amdt_words[start_idx:end_idx] != keyword_words:
                    continue

                for attribution in attributions:
                    results.append(
                        {
                            "amdt_idx": amendment["amdt_idx"],
                            "attribution": attribution,
                            "keyword": keyword,
                            "matcher": KeywordMatcher,
                            "matcher_type": self.matcher_type,
                            "column": column_name,
                        }
                    )

        return results

    def get_attribution_comment(self, matches: List[Dict[str, str]]) -> str:
        """
        Generate a comment explaining the keyword-based attribution.

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
            comments.append(f"Affectations par mots clés dans '{column}' :")
            column_matches = [m for m in matches if m["column"] == column]
            attributions = {match["attribution"] for match in column_matches}
            for attribution in sorted(attributions):
                keyword_counts: Counter[str] = Counter(
                    m["keyword"]
                    for m in column_matches
                    if m["attribution"] == attribution
                )
                attribution_keywords = sorted(
                    keyword_counts.items(), key=lambda x: x[0]
                )
                formatted_keywords = ", ".join(
                    f"{keyword} (x{count})" for keyword, count in attribution_keywords
                )
                comments.append(f"{attribution} : [{formatted_keywords}]")

        return "\n".join(comments)
