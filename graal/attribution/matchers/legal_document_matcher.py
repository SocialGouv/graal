"""Matcher implementation for legal document-based matching (codes, laws, ordonnances)."""

import logging
import logging.config
import re
from typing import Any, Pattern

import pandas as pd

from graal.attribution.matchers.base_matcher import BaseMatcher
from graal.custom_types import AttributionMatcherType, ColumnName, LegalDocumentType

logging.config.fileConfig("logging.conf")


class LegalDocumentMatcher(BaseMatcher):
    """Matches amendments based on legal document (code/law/ordonnance) and article presence."""

    def __init__(
        self,
        document_type: LegalDocumentType,
        documents_df: pd.DataFrame,
        allowed_columns: set[ColumnName],
        matcher_type: AttributionMatcherType,
    ):
        """
        Initialize the LegalDocumentMatcher.

        Args:
            document_type: Type of legal document to match (CODE, LAW, ORDONNANCE)
            documents_df: DataFrame containing legal document data with columns:
                        - value: normalized document text
                        - Articles: normalized article text
                        - Affectation (nom): attribution name
            articles_set: Set of all possible articles
        """
        super().__init__(matcher_type=matcher_type)
        self.document_type = document_type
        self.documents_df = documents_df
        self.allowed_columns = allowed_columns or {"Corps amdt"}
        self.document_patterns = self._compile_document_patterns()
        self.article_pattern = self._compile_article_pattern()

    def _compile_document_patterns(self) -> list[Pattern[str]]:
        """Compile regex patterns for legal document matching."""
        documents_set = set(self.documents_df["value"])

        if self.document_type == LegalDocumentType.CODE:
            return [
                re.compile(
                    rf"code\s(?:general\sdes|des|du|de|de\sla|d')?\s?((?:{'|'.join(documents_set)}))"
                )
            ]
        elif self.document_type == LegalDocumentType.LAW:
            return [
                re.compile(
                    r"\sloi\s(?:n.?(?:deg)?\s?)((?:(?:\d+-\d+)\s+)?du\s+(?:\d+\s\w+\s\d{4}))"
                ),
                re.compile(r"\sloi\s(du\s+(?:\d+\s\w+\s\d{4}))"),
            ]
        elif self.document_type == LegalDocumentType.ORDONNANCE:
            return [
                re.compile(
                    r"ordonnance\s(?:n.?(?:deg)?\s?)((?:(?:\d+-\d+)\s+)?du\s+(?:\d+\s\w+\s\d{4}))"
                )
            ]
        else:
            raise ValueError(f"Unsupported document type: {self.document_type}")

    def _compile_article_pattern(self) -> Pattern[str]:
        """Compile regex pattern for article matching."""
        latin_ordinal_pattern = re.compile(r"(?:\d+(?:-\d+)*)(?:\s(.+))?")
        latin_ordinals_set = {
            match.group(1)
            for article in self.documents_df["Articles"]
            if (match := latin_ordinal_pattern.match(article)) and match.group(1)
        }
        possible_ordinals_pattern = "|".join(sorted(latin_ordinals_set, reverse=True))
        return re.compile(
            rf"(?:(?:l\.|articles?|art\.?))(?:\set\s|\s?(\d+(?:-\d+)*(?:\s?(?:{possible_ordinals_pattern}))?))+"
        )

    def match(
        self, amendment: dict[str, Any], column_name: str
    ) -> list[dict[str, str]]:
        """
        Match legal documents and articles against amendment text.

        Args:
            amendment: Dictionary containing amendment data
            column_name: Name of the column to match against

        Returns:
            List of dictionaries containing match information
        """
        if column_name not in self.allowed_columns:
            return []
        normalized_text = amendment[column_name]

        # Find all legal document matches
        matched_documents = set()
        for pattern in self.document_patterns:
            matches = re.findall(pattern, normalized_text)
            if matches:
                matched_documents.update(matches)

        if not matched_documents:
            return []

        # Find article matches
        article_matches = set(re.findall(self.article_pattern, normalized_text))
        matched_articles = {
            article.strip() for article in article_matches
        }.intersection(self.documents_df["Articles"])

        if not matched_articles:
            return []

        # Find matching rows in documents DataFrame
        results = []
        matching_rows = self.documents_df[
            self.documents_df["value"].isin(matched_documents)
            & self.documents_df["Articles"].isin(matched_articles)
        ]

        for _, row in matching_rows.iterrows():
            results.append(
                {
                    "amdt_idx": amendment["amdt_idx"],
                    "attribution": row["Affectation (nom)"],
                    "document": row["value"],
                    "article": row["Articles"],
                    "document_type": self.document_type.value,
                    "matcher": LegalDocumentMatcher,
                    "matcher_type": self.matcher_type,
                    "column": column_name,
                }
            )

        return results

    def get_attribution_comment(self, matches: list[dict[str, str]]) -> str:
        """
        Generate a comment explaining the legal document-based attribution.

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
                f"Affectations par {self.document_type.value}s dans '{column}' :"
            )
            column_matches = [m for m in matches if m["column"] == column]
            attributions = {match["attribution"] for match in column_matches}

            for attribution in sorted(attributions):
                document_articles = sorted(
                    {
                        f"{document} (articles {', '.join(sorted({m['article'] for m in column_matches if m['attribution'] == attribution}))})"
                        for document in {
                            m["document"]
                            for m in column_matches
                            if m["attribution"] == attribution
                        }
                    }
                )
                comments.append(f"{attribution} : {', '.join(document_articles)}")

        return "\n".join(comments)
