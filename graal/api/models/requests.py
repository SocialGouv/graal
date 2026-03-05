"""
API request models.
"""

import re
from typing import Any, ClassVar, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from graal.database.enums import DbRoleEnum, ExcelConfigRoleEnum


class AssignPermissionRequest(BaseModel):
    """Request model for assigning database permissions."""

    user_id: UUID = Field(..., description="User ID (UUID) to grant permission to")
    role: DbRoleEnum = Field(..., description="Role to assign")


class ExcelConfigPermissionRequest(BaseModel):
    """Request for assigning Excel config permissions."""

    user_id: UUID = Field(..., description="Target user ID")
    role: ExcelConfigRoleEnum = Field(
        ..., description="Role to assign (owner or reader)"
    )


class ExcelConfigPermissionDeleteRequest(BaseModel):
    """Request body for removing a specific Excel config permission."""

    user_id: UUID = Field(..., description="User ID to remove")


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

    database_id: Optional[UUID] = Field(
        default=None,
        description="UUID of the similarity database manifest. Required when similarity search is enabled.",
    )
    origin_project: Optional[str] = Field(
        default=None,
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


class SummaryGenerationConfig(BaseModel):
    """Configuration for summary generation (Objet amdt) feature."""

    enabled: bool = Field(
        default=False, description="Whether summary generation feature is enabled"
    )
    should_overwrite: bool = Field(
        default=True,
        description="If true, overwrite existing values; if false, preserve existing values",
    )
    # New UI prefers selecting an admin-managed LLM config.
    llm_config_id: Optional[UUID] = Field(
        default=None,
        description="UUID of an admin-managed LLM config to use when enabled.",
    )

    @field_validator("llm_config_id")
    @classmethod
    def validate_llm_selection_when_enabled(cls, v, info):
        """Validate that an LLM config id is provided when summary generation is enabled."""

        data = info.data
        if not data.get("enabled"):
            return v

        if v is None:
            raise ValueError(
                "llm_config_id is required when summary generation is enabled"
            )

        return v


class ProcessingConfig(BaseModel):
    """Configuration model for processing parameters."""

    # Dynamic filter for missions (read from uploaded JSON in frontend)
    mission_short_title_filter: Optional[list[str]] = Field(
        default=None,
        description=(
            "List of mission short titles to keep. "
            "If omitted, keep backend/config defaults. "
            "If provided as an empty list, means no mission filtering."
        ),
    )

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
    summary_generation: Optional[SummaryGenerationConfig] = Field(
        default_factory=SummaryGenerationConfig,
        description="Summary generation (Objet amdt) feature configuration",
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
    def _validate_threshold_dict(
        cls, thresholds: Dict[str, float], dict_name: str, description: str
    ) -> None:
        """Validate a dictionary of similarity thresholds by column.

        Args:
            thresholds: Dictionary mapping column names to threshold values
            dict_name: Name of the dictionary (for error messages)
            description: Human-readable description of the threshold type
        """
        for column, threshold in thresholds.items():
            if column not in cls.VALID_COLUMNS:
                raise ValueError(
                    f"Invalid column '{column}' in {dict_name}. Must be one of: {cls.VALID_COLUMNS}"
                )
            cls._validate_threshold_range(threshold, f"{description} for '{column}'")

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
        if not params:
            return params

        # When the feature is disabled, accept empty strings from the UI
        # and normalize to None so optional Field constraints don't trip.
        if not params.enabled:
            if params.origin_project is not None and not params.origin_project.strip():
                params.origin_project = None
            return params

        if params.enabled:
            # Validate database_id is provided when enabled
            if not params.database_id:
                raise ValueError(
                    "database_id is required when similarity search is enabled. "
                    "Please select a similarity database."
                )

            params.origin_project = cls._validate_origin_project(params.origin_project)
            cls._validate_threshold_dict(
                params.clustering_similarity_thresholds,
                "clustering_similarity_thresholds",
                "Clustering similarity threshold",
            )
            cls._validate_threshold_dict(
                params.fuzzy_match_similarity_thresholds,
                "fuzzy_match_similarity_thresholds",
                "Fuzzy match similarity threshold",
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
        Future-proof: Automatically checks all fields with an 'enabled' attribute.

        Returns:
            True if at least one feature is enabled, False otherwise
        """
        # Iterate through all fields in this model
        # and check if any have an 'enabled' attribute set to True
        for field_name in self.model_fields:
            field_value = getattr(self, field_name, None)
            # Check if the field is an object with an 'enabled' attribute
            if (
                field_value is not None
                and hasattr(field_value, "enabled")
                and field_value.enabled is True
            ):
                return True
        return False


class ProcessingRequest(BaseModel):
    """Request model for processing amendments."""

    config_file_id: str = Field(
        ...,
        min_length=36,
        max_length=36,
        description="UUID of the Excel configuration manifest (ExcelConfigManifest.id)",
    )
    processing_config: ProcessingConfig = Field(
        ..., description="Processing configuration parameters"
    )

    @field_validator("config_file_id")
    @classmethod
    def validate_config_file_id(cls, v: str) -> str:
        """Validate that config_file_id is a valid UUID."""
        if not v or not v.strip():
            raise ValueError("config_file_id cannot be empty")

        v = v.strip()

        try:
            UUID(v)
        except ValueError as exc:
            raise ValueError(
                "config_file_id must be a valid UUID (e.g. '3f7a8b2c-1234-5678-abcd-ef0123456789')"
            ) from exc

        return v


class FileUploadMetadata(BaseModel):
    """Metadata for file upload operations."""

    default_processing_timestamp: int = Field(
        ..., description="Unix timestamp for processing"
    )
    origin_project: str = Field(..., description="Origin project name")


class FileUploadReference(BaseModel):
    """Reference to an uploaded file."""

    upload_id: str = Field(..., description="Upload ID from file upload")
    filename: str = Field(..., description="Original filename")
    file_hash: str = Field(..., description="SHA256 hash of file content")
    s3_key: str = Field(..., description="S3 key where file is stored in pool")
    metadata: FileUploadMetadata = Field(..., description="File processing metadata")


class BaseDatabaseOperationRequest(BaseModel):
    """Base model for database operations with shared configuration fields."""

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

    @staticmethod
    def _validate_file_references_list(v: list[Any]) -> list[Any]:
        """Validate that file_references has at least one file."""
        if not v or len(v) < 1:
            raise ValueError("At least one file must be provided")
        return v


class DatabaseBuildRequest(BaseDatabaseOperationRequest):
    """Request to build a similarity database."""

    config_file_id: str = Field(
        ...,
        min_length=36,
        max_length=36,
        description="UUID of the Excel configuration manifest to use",
    )
    database_name: str = Field(
        ..., description="Name for the database (without extension)", min_length=1
    )
    file_references: list[FileUploadReference] = Field(
        ..., description="References to uploaded files"
    )

    @field_validator("config_file_id")
    @classmethod
    def validate_config_file_id(cls, v: str) -> str:
        """Validate that config_file_id is a valid UUID."""
        if not v or not v.strip():
            raise ValueError("config_file_id cannot be empty")
        v = v.strip()
        try:
            UUID(v)
        except ValueError as exc:
            raise ValueError("config_file_id must be a valid UUID") from exc
        return v

    @field_validator("file_references")
    @classmethod
    def validate_file_references(
        cls, v: list[FileUploadReference]
    ) -> list[FileUploadReference]:
        """Validate that file_references has at least one file."""
        return cls._validate_file_references_list(v)


class AppendDatabaseRequest(BaseDatabaseOperationRequest):
    """Request to append files to an existing database."""

    config_file_id: str = Field(
        ...,
        min_length=36,
        max_length=36,
        description="UUID of the Excel configuration manifest to use",
    )
    file_references: list[FileUploadReference] = Field(
        ..., description="References to new files to append"
    )

    @field_validator("config_file_id")
    @classmethod
    def validate_config_file_id(cls, v: str) -> str:
        """Validate that config_file_id is a valid UUID."""
        if not v or not v.strip():
            raise ValueError("config_file_id cannot be empty")
        v = v.strip()
        try:
            UUID(v)
        except ValueError as exc:
            raise ValueError("config_file_id must be a valid UUID") from exc
        return v

    @field_validator("file_references")
    @classmethod
    def validate_file_references(
        cls, v: list[FileUploadReference]
    ) -> list[FileUploadReference]:
        """Validate that file_references has at least one file."""
        return cls._validate_file_references_list(v)


class DeleteFilesFromDatabaseRequest(BaseDatabaseOperationRequest):
    """Request to delete files from an existing database and rebuild it.

    The files identified by ``file_hashes_to_delete`` are removed from the
    database manifest and a full rebuild is triggered with the remaining files.
    Files in the S3 input pool are *not* deleted, because they may be shared
    with other databases.
    """

    config_file_id: str = Field(
        ...,
        min_length=36,
        max_length=36,
        description="UUID of the Excel configuration manifest to use for rebuilding",
    )
    file_hashes_to_delete: list[str] = Field(
        ..., description="SHA-256 hashes of the files to remove from the database"
    )

    @field_validator("config_file_id")
    @classmethod
    def validate_config_file_id(cls, v: str) -> str:
        """Validate that config_file_id is a valid UUID."""
        if not v or not v.strip():
            raise ValueError("config_file_id cannot be empty")
        v = v.strip()
        try:
            UUID(v)
        except ValueError as exc:
            raise ValueError("config_file_id must be a valid UUID") from exc
        return v

    @field_validator("file_hashes_to_delete")
    @classmethod
    def validate_file_hashes_to_delete(cls, v: list[str]) -> list[str]:
        """Validate that at least one hash is provided."""
        if not v:
            raise ValueError(
                "At least one file hash must be provided in file_hashes_to_delete"
            )
        return v
