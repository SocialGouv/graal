"""
Feature-specific text normalizers that don't affect original data.

Each feature gets its own normalizer to avoid cross-dependencies
and side effects from shared normalization functions.
"""

import re
from abc import ABC

from unidecode import unidecode

from graal.core.feature_interface import FeatureTextNormalizer
from graal.custom_types import FeatureName
from graal.utils.text_utils import (
    digitize_small_french_numbers,
    remove_french_plurals,
    remove_small_roman_numerals,
    remove_stop_words,
)


class BaseTextNormalizer(FeatureTextNormalizer, ABC):
    """
    Base class for text normalizers with common normalization steps.

    Provides reusable normalization methods that can be composed
    differently by each feature-specific normalizer.
    """

    def _remove_roman_numerals(self, text: str) -> str:
        """Remove small roman numerals from text."""
        return remove_small_roman_numerals(text)

    def _apply_unidecode_and_lowercase(self, text: str) -> str:
        """Apply unidecode and convert to lowercase."""
        return unidecode(text).strip().lower()

    def _handle_apostrophes_and_underscores(self, text: str) -> str:
        """Replace apostrophes, backticks, underscores with spaces."""
        return re.sub(r"['`'_]", " ", text)

    def _handle_dashes(self, text: str) -> str:
        """Replace dashes with spaces unless they are surrounded by numbers."""
        return re.sub(r"(?<!\d)-(?!\d)", " ", text)

    def _remove_special_characters(
        self, text: str, pattern: str = r"[^a-zA-Z0-9\s\-%]"
    ) -> str:
        """Remove special characters based on the provided pattern."""
        return re.sub(pattern, "", text)

    def _handle_unicode_spaces(self, text: str) -> str:
        """Replace various Unicode space characters with regular spaces."""
        return re.sub(
            r"[\u00A0\u1680\u180E\u2000-\u200B\u202F\u205F\u3000]",
            " ",
            text,
        )

    def _remove_stop_words(self, text: str) -> str:
        """Remove French stop words."""
        return remove_stop_words(text)

    def _digitize_numbers(self, text: str) -> str:
        """Convert French number words to digits."""
        return digitize_small_french_numbers(text)

    def _remove_plurals(self, text: str) -> str:
        """Remove French plurals from words."""
        return " ".join(remove_french_plurals(word) for word in text.split())

    def _clean_whitespace(self, text: str) -> str:
        """Remove extra whitespaces and strip."""
        return re.sub(r"\s+", " ", text).strip()

    def _apply_standard_similarity_normalization(self, text: str) -> str:
        """
        Apply the standard normalization pipeline used by similarity-based features.

        This method encapsulates the common normalization steps shared by
        similarity search, allotment, and similarities within lectures features.
        """
        if not text:
            return ""

        text = self._remove_roman_numerals(text)
        text = self._apply_unidecode_and_lowercase(text)
        text = self._handle_apostrophes_and_underscores(text)
        text = self._handle_dashes(text)
        text = self._remove_special_characters(text)
        text = self._remove_stop_words(text)
        text = self._digitize_numbers(text)
        text = self._remove_plurals(text)
        text = self._clean_whitespace(text)

        return text


class AttributionTextNormalizer(BaseTextNormalizer):
    """
    Text normalizer for attribution feature.

    Focuses on preserving keywords and proper nouns that matter
    for attribution matching while standardizing format.
    """

    def normalize_for_feature(self, text: str) -> str:
        """Normalize text for attribution matching."""
        if not text:
            return ""

        text = self._remove_roman_numerals(text)
        text = self._apply_unidecode_and_lowercase(text)
        text = self._handle_dashes(text)
        text = self._handle_unicode_spaces(text)

        # Attribution-specific: split on punctuation and remove plurals
        split_pattern = r"[\s\n\r\t\f'.,;:!?\"(){}<>-\[\]]+"
        text = "".join(
            remove_french_plurals(word) for word in re.split(f"({split_pattern})", text)
        )

        text = self._clean_whitespace(text)
        return text


class SimilaritySearchTextNormalizer(BaseTextNormalizer):
    """
    Text normalizer for similarity search feature.

    Optimized for finding similar amendments by normalizing in a way
    that emphasizes semantic content over format.
    """

    def normalize_for_feature(self, text: str) -> str:
        """Normalize text for similarity search."""
        return self._apply_standard_similarity_normalization(text)


class SummaryTextNormalizer(BaseTextNormalizer):
    """
    Text normalizer for summary generation feature.

    Preserves readability and important formatting while cleaning
    text for LLM processing.
    """

    def normalize_for_feature(self, text: str) -> str:
        """Normalize text for summary generation."""
        if not text:
            return ""

        cleaned_text = self._apply_unidecode_and_lowercase(text)
        cleaned_text = cleaned_text.replace("'", "'")

        cleaned_text = cleaned_text.replace("\n", " ").replace("\r", "")
        cleaned_text = self._handle_unicode_spaces(cleaned_text)

        # Keep more characters for readability in summaries
        cleaned_text = re.sub(r"[^a-z0-9À-ÿ'.,!? \-«»\"]+", "", cleaned_text)

        cleaned_text = self._clean_whitespace(cleaned_text)
        return cleaned_text


class AllotmentTextNormalizer(BaseTextNormalizer):
    """
    Text normalizer for allotment feature.

    Optimized for detecting exact or near-exact duplicates,
    so it's more aggressive in normalization.
    """

    def normalize_for_feature(self, text: str) -> str:
        """Normalize text for allotment/clustering."""
        return self._apply_standard_similarity_normalization(text)


class SimilaritiesWithinLecturesTextNormalizer(BaseTextNormalizer):
    """
    Text normalizer for similarities within lectures feature.

    Similar to similarity search but may have different thresholds
    and requirements for within-document similarity.
    """

    def normalize_for_feature(self, text: str) -> str:
        """Normalize text for similarities within lectures."""
        return self._apply_standard_similarity_normalization(text)


class TextNormalizerFactory:
    """Factory for creating feature-specific text normalizers."""

    _normalizers: dict[FeatureName, FeatureTextNormalizer] = {
        "attribution": AttributionTextNormalizer(),
        "similarity_search": SimilaritySearchTextNormalizer(),
        "summary_generation": SummaryTextNormalizer(),
        "allotment": AllotmentTextNormalizer(),
        "similarities_within_lectures": SimilaritiesWithinLecturesTextNormalizer(),
    }

    @staticmethod
    def get_normalizer(feature_name: FeatureName) -> FeatureTextNormalizer:
        """Get the appropriate normalizer for a feature."""
        if feature_name not in TextNormalizerFactory._normalizers:
            raise ValueError(f"No normalizer found for feature: {feature_name}")
        return TextNormalizerFactory._normalizers[feature_name]
