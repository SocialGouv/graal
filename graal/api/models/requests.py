"""
API request models.
"""

import re
from typing import ClassVar, Dict, Optional

from pydantic import BaseModel, Field, field_validator


class AllotmentsConfig(BaseModel):
    """Configuration for allotments feature."""

    enabled: bool = Field(
        default=False, description="Whether allotments feature is enabled"
    )
    column: str = Field(
        default="Corps amdt", description="Column used for similarity comparison"
    )
    similarity_threshold: float = Field(
        default=0.999,
        ge=0.0,
        le=1.0,
        description="Threshold above which amendments are considered similar",
    )


class SimilaritiesWithinLecturesConfig(BaseModel):
    """Configuration for similarities within lectures feature."""

    enabled: bool = Field(
        default=False,
        description="Whether similarities within lectures feature is enabled",
    )
    column: str = Field(
        default="Exposé amdt", description="Column used for similarity comparison"
    )
    similarity_threshold: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Threshold above which amendments are considered similar",
    )


class ColumnToCopyConfig(BaseModel):
    """Configuration for a column to copy from similar amendments."""

    enabled: bool = Field(
        default=True, description="Whether this column should be copied"
    )
    condition: Optional[str] = Field(
        default=None,
        description="Optional condition that must match to copy this column",
    )


class SimilaritySearchConfig(BaseModel):
    """Configuration for similarity search feature."""

    enabled: bool = Field(
        default=False, description="Whether similarity search feature is enabled"
    )
    origin_project: Optional[str] = Field(
        default=None,
        min_length=2,
        max_length=100,
        description="Name of the legislative project for similarity search (e.g., 'PLFSS 2025')",
    )
    clustering_similarity_thresholds: Dict[str, float] = Field(
        default_factory=lambda: {"Exposé amdt": 0.4, "Corps amdt": 0.4},
        description="Clustering similarity thresholds for initial TF-IDF clustering by column",
    )
    fuzzy_match_similarity_thresholds: Dict[str, float] = Field(
        default_factory=lambda: {"Exposé amdt": 0.4, "Corps amdt": 0.9},
        description="Fuzzy match similarity thresholds for precise Damerau-Levenshtein comparison by column",
    )
    similarity_threshold_overrides: Dict[str, Dict[str, float]] = Field(
        default_factory=dict,
        description="Similarity threshold overrides for specific columns and amendment types (like 'amendement redactionnel')",
    )
    columns_to_copy: Dict[str, ColumnToCopyConfig] = Field(
        default_factory=lambda: {
            "Réponse": ColumnToCopyConfig(enabled=True),
            "Sort": ColumnToCopyConfig(enabled=True, condition="irrecevable"),
            "Objet amdt": ColumnToCopyConfig(enabled=False),
        },
        description="Configuration for which columns to copy from similar amendments",
    )


class AttributionConfig(BaseModel):
    """Configuration for attribution feature."""

    enabled: bool = Field(
        default=True, description="Whether attribution feature is enabled"
    )
    project_name: str = Field(default="PLF", description="Project name for attribution")


class DefaultOpinionConfig(BaseModel):
    """Configuration for default opinion feature."""

    enabled: bool = Field(
        default=False, description="Whether default opinion feature is enabled"
    )


class ProcessingConfig(BaseModel):
    """Configuration model for processing parameters."""

    # Feature configurations
    allotments: Optional[AllotmentsConfig] = Field(
        default_factory=AllotmentsConfig, description="Allotments feature configuration"
    )
    similarities_within_lectures: Optional[SimilaritiesWithinLecturesConfig] = Field(
        default_factory=SimilaritiesWithinLecturesConfig,
        description="Similarities within lectures feature configuration",
    )
    similarity_search: Optional[SimilaritySearchConfig] = Field(
        default_factory=SimilaritySearchConfig,
        description="Similarity search feature configuration",
    )
    attribution: Optional[AttributionConfig] = Field(
        default_factory=AttributionConfig,
        description="Attribution feature configuration",
    )
    default_opinion: Optional[DefaultOpinionConfig] = Field(
        default_factory=DefaultOpinionConfig,
        description="Default opinion feature configuration",
    )

    # Constants for validation
    VALID_COLUMNS: ClassVar[list[str]] = ["Corps amdt", "Exposé amdt"]

    @classmethod
    def _validate_origin_project(cls, origin_project: Optional[str]) -> str:
        """Validate origin project field."""
        if not origin_project:
            raise ValueError(
                "Origin project is required when similarity search is enabled"
            )

        origin_project = origin_project.strip()

        if len(origin_project) < 2:
            raise ValueError("Origin project must be at least 2 characters long")

        if len(origin_project) > 100:
            raise ValueError("Origin project cannot exceed 100 characters")

        # Security validation: only allow alphanumeric, spaces, hyphens, underscores, and common punctuation
        if not re.match(r"^[a-zA-Z0-9\s\-_.,()\/]+$", origin_project):
            raise ValueError("Origin project contains invalid characters")

        return origin_project

    @classmethod
    def _validate_threshold_range(cls, threshold: float, context: str) -> None:
        """Validate that a threshold is within the valid range [0.0, 1.0]."""
        if not (0.0 <= threshold <= 1.0):
            raise ValueError(f"{context} must be between 0.0 and 1.0")

    @classmethod
    def _validate_clustering_thresholds(cls, thresholds: Dict[str, float]) -> None:
        """Validate clustering similarity thresholds."""
        for column, threshold in thresholds.items():
            if column not in cls.VALID_COLUMNS:
                raise ValueError(
                    f"Invalid column '{column}' in clustering_similarity_thresholds. Must be one of: {cls.VALID_COLUMNS}"
                )
            cls._validate_threshold_range(
                threshold, f"Clustering similarity threshold for '{column}'"
            )

    @classmethod
    def _validate_fuzzy_match_thresholds(cls, thresholds: Dict[str, float]) -> None:
        """Validate fuzzy match similarity thresholds."""
        for column, threshold in thresholds.items():
            if column not in cls.VALID_COLUMNS:
                raise ValueError(
                    f"Invalid column '{column}' in fuzzy_match_similarity_thresholds. Must be one of: {cls.VALID_COLUMNS}"
                )
            cls._validate_threshold_range(
                threshold, f"Fuzzy match similarity threshold for '{column}'"
            )

    @classmethod
    def _validate_threshold_overrides(
        cls, overrides: Dict[str, Dict[str, float]]
    ) -> None:
        """Validate similarity threshold overrides."""
        for column, column_overrides in overrides.items():
            if column not in cls.VALID_COLUMNS:
                raise ValueError(
                    f"Invalid column '{column}' in similarity_threshold_overrides. Must be one of: {cls.VALID_COLUMNS}"
                )
            for amendment_type, threshold in column_overrides.items():
                cls._validate_threshold_range(
                    threshold,
                    f"Similarity threshold override for '{amendment_type}' in column '{column}'",
                )

    @field_validator("similarity_search")
    @classmethod
    def validate_similarity_search(
        cls, params: SimilaritySearchConfig
    ) -> SimilaritySearchConfig:
        """Validate similarity search configuration."""
        if params and params.enabled:
            params.origin_project = cls._validate_origin_project(params.origin_project)
            cls._validate_clustering_thresholds(params.clustering_similarity_thresholds)
            cls._validate_fuzzy_match_thresholds(
                params.fuzzy_match_similarity_thresholds
            )
            cls._validate_threshold_overrides(params.similarity_threshold_overrides)

        return params

    @field_validator("allotments", "similarities_within_lectures", "attribution")
    @classmethod
    def validate_column_choices(cls, v, info):
        """Validate column choices for features that use them."""
        if v and hasattr(v, "column"):
            valid_columns = ["Corps amdt", "Exposé amdt"]
            if v.column not in valid_columns:
                raise ValueError(f"Column must be one of: {valid_columns}")
        return v

    @field_validator("attribution")
    @classmethod
    def validate_project_name(cls, v):
        """Validate project name for attribution."""
        if v and v.project_name:
            valid_projects = ["PLF", "PLFSS"]
            if v.project_name not in valid_projects:
                raise ValueError(f"Project name must be one of: {valid_projects}")
        return v


class ProcessingRequest(BaseModel):
    """Request model for processing amendments."""

    processing_config: ProcessingConfig = Field(
        ..., description="Processing configuration parameters"
    )
