"""
API request models.
"""

import re
from typing import ClassVar, Dict, Optional

from pydantic import BaseModel, Field, field_validator


class AllotmentConfig(BaseModel):
    """Configuration for allotment feature."""

    enabled: bool = Field(
        default=False, description="Whether allotment feature is enabled"
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
    database_file: Optional[str] = Field(
        default=None,
        description="S3 path to the Parquet database file (e.g., 'PLFSS/2024.parquet'). Required when similarity search is enabled.",
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
    should_overwrite: bool = Field(
        default=True,
        description="If true, overwrite existing values; if false, preserve existing values",
    )


class AttributionConfig(BaseModel):
    """Configuration for attribution feature."""

    enabled: bool = Field(
        default=True, description="Whether attribution feature is enabled"
    )
    project_name: str = Field(default="PLF", description="Project name for attribution")
    should_overwrite: bool = Field(
        default=True,
        description="If true, overwrite existing values; if false, preserve existing values",
    )


class DefaultOpinionConfig(BaseModel):
    """Configuration for default opinion feature."""

    enabled: bool = Field(
        default=False, description="Whether default opinion feature is enabled"
    )
    should_overwrite: bool = Field(
        default=True,
        description="If true, overwrite existing values; if false, preserve existing values",
    )


class ProcessingConfig(BaseModel):
    """Configuration model for processing parameters."""

    # Feature configurations
    allotment: Optional[AllotmentConfig] = Field(
        default_factory=AllotmentConfig, description="Allotment feature configuration"
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

    # Processing options (pipeline-level)
    placeholder_amdt_body: bool = Field(
        default=False,
        description="If true, use placeholder text for empty amendment bodies",
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
            # Validate database_file is provided when enabled
            if not params.database_file:
                raise ValueError(
                    "database_file is required when similarity search is enabled. "
                    "Please select a similarity database."
                )

            params.origin_project = cls._validate_origin_project(params.origin_project)
            cls._validate_clustering_thresholds(params.clustering_similarity_thresholds)
            cls._validate_fuzzy_match_thresholds(
                params.fuzzy_match_similarity_thresholds
            )
            cls._validate_threshold_overrides(params.similarity_threshold_overrides)

        return params

    @field_validator("allotment", "similarities_within_lectures", "attribution")
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

    def has_any_feature_enabled(self) -> bool:
        """
        Check if at least one feature is enabled.

        Returns:
            True if at least one feature is enabled, False otherwise
        """
        return bool(
            (self.allotment and self.allotment.enabled)
            or (
                self.similarities_within_lectures
                and self.similarities_within_lectures.enabled
            )
            or (self.similarity_search and self.similarity_search.enabled)
            or (self.attribution and self.attribution.enabled)
            or (self.default_opinion and self.default_opinion.enabled)
        )


class ProcessingRequest(BaseModel):
    """Request model for processing amendments."""

    config_file: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Name of the configuration Excel file from S3",
    )
    processing_config: ProcessingConfig = Field(
        ..., description="Processing configuration parameters"
    )

    @field_validator("config_file")
    @classmethod
    def validate_config_file(cls, v: str) -> str:
        """Validate config_file field."""
        if not v or not v.strip():
            raise ValueError("config_file cannot be empty")

        v = v.strip()

        if not v.endswith(".xlsx"):
            raise ValueError("config_file must be an Excel file (.xlsx)")

        # Security: only safe characters allowed (including Unicode letters)
        if not re.match(r"^[a-zA-Z0-9\u00C0-\u024F\s\-_\.()]+\.xlsx$", v):
            raise ValueError("config_file contains invalid characters")

        return v


class FileUploadReference(BaseModel):
    """Reference to an uploaded file."""

    upload_id: str = Field(..., description="Upload ID from file upload")
    filename: str = Field(..., description="Original filename")
    default_processing_timestamp: int = Field(
        ..., description="Unix timestamp for processing"
    )
    origin_project: str = Field(..., description="Origin project name")


class DatabaseBuildRequest(BaseModel):
    """Request to build a similarity database."""

    config_file: str = Field(
        ..., description="Office configuration Excel file to use", min_length=1
    )
    database_name: str = Field(
        ..., description="Name for the database (without extension)", min_length=1
    )
    file_references: list[FileUploadReference] = Field(
        ..., description="References to uploaded files"
    )
    drop_empty_columns: list[str] = Field(
        default=["Réponse"],
        description="Columns where empty rows should be dropped",
    )
    similarity_threshold: float = Field(
        default=0.99,
        ge=0.0,
        le=1.0,
        description="Threshold for Levenshtein refinement",
    )
    eps: float = Field(
        default=0.4, ge=0.0, le=1.0, description="Epsilon value for DBSCAN clustering"
    )
    group_by_columns: list[str] = Field(
        default=["Lecture", "origin_project", "Num article"],
        description="Columns to group by during clustering",
    )

    @field_validator("file_references")
    @classmethod
    def validate_file_references(
        cls, v: list[FileUploadReference]
    ) -> list[FileUploadReference]:
        """Validate that file_references has at least one file."""
        if not v or len(v) < 1:
            raise ValueError("At least one file must be provided")
        return v
