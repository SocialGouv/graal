"""Matcher implementation for keyword-based matching."""

import re
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

            for word in keyword_words:
                # Find all starting positions where this word matches
                start_indexes = [i for i, w in enumerate(amdt_words) if w == word]

                for start_idx in start_indexes:
                    if start_idx != -1:
                        end_idx = start_idx + len(keyword_words)
                        # Check if all following words match in sequence
                        if amdt_words[start_idx:end_idx] == keyword_words:
                            # Get attribution(s) for this keyword
                            attributions = self.keywords_df[
                                self.keywords_df["Mots clés"] == keyword
                            ]["Affectation (nom)"].tolist()

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
                            break  # Once we find a match for this word, move to next keyword

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
                attribution_keywords = sorted(
                    {
                        m["keyword"]
                        for m in column_matches
                        if m["attribution"] == attribution
                    }
                )
                comments.append(f"{attribution} : [{', '.join(attribution_keywords)}]")

        return "\n".join(comments)
