"""
Core interfaces for feature processing in GRAAL.

This module defines the base interfaces that ensure features can operate
independently without side effects or dependencies on other features.

Note: Some features like allotment may be registered as preprocessing features
that run first and can filter data, but they still use the same BaseFeature interface.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Set

import pandas as pd


@dataclass
class FeatureInput:
    """Immutable input data for a feature."""

    amendments_df: pd.DataFrame
    config: Dict[str, Any]

    def __post_init__(self):
        """Ensure the DataFrame is copied to prevent mutations."""
        # Create a deep copy to ensure immutability
        self.amendments_df = self.amendments_df.copy(deep=True)


@dataclass
class FeatureOutput:
    """Output from a feature processing."""

    amendments_df: pd.DataFrame
    # Simple outputs dictionary for any data features want to share
    outputs: Dict[str, Any] = None

    def __post_init__(self):
        if self.outputs is None:
            self.outputs = {}


class BaseFeature(ABC):
    """
    Base class for all features.

    Features:
    1. Work with their own copy of data
    2. Don't modify input data
    3. Apply their own normalization internally
    4. Return clean results without side effects
    5. Can run in any order (some features may be registered as preprocessing)
    """

    def __init__(self, feature_name: str):
        self.feature_name = feature_name

    @abstractmethod
    def get_required_columns(self) -> Set[str]:
        """Return the set of columns this feature requires."""
        pass

    @abstractmethod
    def get_output_columns(self) -> Set[str]:
        """Return the set of columns this feature will produce/modify."""
        pass

    @abstractmethod
    def is_enabled(self, config: Dict[str, Any]) -> bool:
        """Check if this feature is enabled in the configuration."""
        pass

    @abstractmethod
    def process(self, feature_input: FeatureInput) -> FeatureOutput:
        """
        Process amendments with this feature.

        This method must:
        1. Work only with the provided input data
        2. Not modify the input DataFrame
        3. Apply its own text normalization internally
        4. Return a new DataFrame with results

        Args:
            feature_input: Immutable input containing amendments and config

        Returns:
            FeatureOutput containing processed amendments and metadata
        """
        pass

    def validate_input(self, feature_input: FeatureInput) -> None:
        """Validate that required columns are present."""
        required_cols = self.get_required_columns()
        available_cols = set(feature_input.amendments_df.columns)
        missing_cols = required_cols - available_cols

        if missing_cols:
            raise ValueError(
                f"Feature {self.feature_name} requires columns {missing_cols} "
                f"but they are not available in the input data"
            )


class FeatureTextNormalizer(ABC):
    """
    Base class for feature-specific text normalizers.

    Each feature should have its own normalizer that doesn't affect
    the original data or other features' processing.
    """

    @abstractmethod
    def normalize_for_feature(self, text: str) -> str:
        """
        Normalize text specifically for this feature's needs.

        This should be pure (no side effects) and deterministic.
        """
        pass
