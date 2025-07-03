"""Unit tests for RedactionalAmendmentMatcher."""

import unittest
from unittest.mock import patch

import pandas as pd

from graal.attribution.matchers.redactional_amendment_matcher import (
    RedactionalAmendmentMatcher,
)


class TestRedactionalAmendmentMatcher(unittest.TestCase):
    def setUp(self):
        """Set up test data."""
        # Create test subsidiary table data
        self.subsidiary_data = pd.DataFrame(
            {
                "Numéro article": ["Liminaire", "1", "2"],
                "Affectation (nom)": ["Bob Martin", "Alice Douglas", "Bart Simpson"],
            }
        )

        self.matcher = RedactionalAmendmentMatcher(
            subsidiary_df=self.subsidiary_data,
            allowed_columns={"Exposé amdt", "Corps amdt"},
        )

    def test_match_redactional_amendment_with_valid_article(self):
        """Test matching a redactional amendment with a valid article number."""
        amendment = {
            "amdt_idx": 1,
            "is_redactional": True,
            "Num article": "1",
            "Exposé amdt": "Amendement rédactionnel.",
        }

        matches = self.matcher.match(amendment, "Exposé amdt")

        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["attribution"], "Alice Douglas")
        self.assertEqual(matches[0]["article_number"], "1")
        self.assertEqual(matches[0]["matcher_type"], "REDACTIONAL_AMENDMENT")

    def test_match_redactional_amendment_with_liminaire_article(self):
        """Test matching a redactional amendment with 'Liminaire' article."""
        amendment = {
            "amdt_idx": 2,
            "is_redactional": True,
            "Num article": "Liminaire",
            "Exposé amdt": "Amendement rédactionnel.",
        }

        matches = self.matcher.match(amendment, "Exposé amdt")

        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["attribution"], "Bob Martin")
        self.assertEqual(matches[0]["article_number"], "Liminaire")

    def test_no_match_for_non_redactional_amendment(self):
        """Test that non-redactional amendments are not matched."""
        amendment = {
            "amdt_idx": 3,
            "is_redactional": False,
            "Num article": "1",
            "Exposé amdt": "Some other amendment text.",
        }

        matches = self.matcher.match(amendment, "Exposé amdt")

        self.assertEqual(len(matches), 0)

    def test_no_match_for_invalid_article_number(self):
        """Test that redactional amendments with invalid article numbers return no matches."""
        amendment = {
            "amdt_idx": 4,
            "is_redactional": True,
            "Num article": "999",
            "Exposé amdt": "Amendement rédactionnel.",
        }

        with patch(
            "graal.attribution.matchers.redactional_amendment_matcher.logger"
        ) as mock_logger:
            matches = self.matcher.match(amendment, "Exposé amdt")

            self.assertEqual(len(matches), 0)
            mock_logger.warning.assert_called_once()

    def test_no_match_for_missing_article_number(self):
        """Test that redactional amendments without article numbers return no matches."""
        amendment = {
            "amdt_idx": 5,
            "is_redactional": True,
            "Num article": "",
            "Exposé amdt": "Amendement rédactionnel.",
        }

        with patch(
            "graal.attribution.matchers.redactional_amendment_matcher.logger"
        ) as mock_logger:
            matches = self.matcher.match(amendment, "Exposé amdt")

            self.assertEqual(len(matches), 0)
            mock_logger.warning.assert_called_once()

    def test_no_match_for_disallowed_column(self):
        """Test that matches are not returned for disallowed columns."""
        amendment = {
            "amdt_idx": 6,
            "is_redactional": True,
            "Num article": "1",
            "Some other column": "Amendement rédactionnel.",
        }

        matches = self.matcher.match(amendment, "Some other column")

        self.assertEqual(len(matches), 0)

    def test_get_attribution_comment(self):
        """Test generation of attribution comments."""
        matches = [
            {
                "attribution": "Alice Douglas",
                "article_number": "1",
                "column": "Exposé amdt",
            },
            {
                "attribution": "Bob Martin",
                "article_number": "Liminaire",
                "column": "Exposé amdt",
            },
        ]

        comment = self.matcher.get_attribution_comment(matches)

        self.assertIn(
            "Affectations par amendement rédactionnel dans 'Exposé amdt'", comment
        )
        self.assertIn("Alice Douglas : article 1", comment)
        self.assertIn("Bob Martin : article Liminaire", comment)

    def test_empty_subsidiary_table(self):
        """Test behavior with empty subsidiary table."""
        empty_matcher = RedactionalAmendmentMatcher(
            subsidiary_df=pd.DataFrame(columns=["Numéro article", "Affectation (nom)"]),
            allowed_columns={"Exposé amdt"},
        )

        amendment = {
            "amdt_idx": 7,
            "is_redactional": True,
            "Num article": "1",
            "Exposé amdt": "Amendement rédactionnel.",
        }

        matches = empty_matcher.match(amendment, "Exposé amdt")

        self.assertEqual(len(matches), 0)


if __name__ == "__main__":
    unittest.main()
