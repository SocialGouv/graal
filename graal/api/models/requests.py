"""
API request models.
"""

import re
from typing import Optional

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
        default=0.9999,
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


class SimilaritySearchConfig(BaseModel):
    """Configuration for similarity search feature."""

    enabled: bool = Field(
        default=False, description="Whether similarity search feature is enabled"
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

    origin_project: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Name of the legislative project (e.g., 'PLFSS 2025')",
    )

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

    @field_validator("origin_project")
    @classmethod
    def validate_origin_project(cls, v):
        """Validate origin project with security checks."""
        if not v:
            raise ValueError("Origin project is required")

        v = v.strip()

        if len(v) < 2:
            raise ValueError("Origin project must be at least 2 characters long")

        if len(v) > 100:
            raise ValueError("Origin project cannot exceed 100 characters")

        # Security validation: only allow alphanumeric, spaces, hyphens, underscores, and common punctuation
        if not re.match(r"^[a-zA-Z0-9\s\-_.,()\/]+$", v):
            raise ValueError("Origin project contains invalid characters")

        return v

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
