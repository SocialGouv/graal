"""Base class for all matchers."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List

from graal.custom_types import AttributionMatcherType


class BaseMatcher(ABC):
    """Abstract base class defining the interface for all matchers."""

    def __init__(self, matcher_type: AttributionMatcherType):
        self.matcher_type = matcher_type
        super().__init__()

    @abstractmethod
    def match(
        self, amendment: Dict[str, Any], column_name: str
    ) -> List[Dict[str, str]]:
        """
        Match the amendment text against the matcher's criteria.

        Args:
            amendment: Dictionary containing amendment data
            column_name: Name of the column to match against

        Returns:
            List of dictionaries containing match information with at least:
            - amdt_idx: The amendment index
            - attribution: The name to attribute to
        """
        pass

    @abstractmethod
    def get_attribution_comment(self, matches: List[Dict[str, str]]) -> str:
        """
        Generate a comment explaining the attribution based on matches.

        Args:
            matches: List of match dictionaries from the match() method

        Returns:
            String containing the attribution comment
        """
        pass
