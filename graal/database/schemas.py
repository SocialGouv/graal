"""Pydantic schemas for database models.

These schemas provide validation and serialization for API requests and responses
related to database models.
"""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserBase(BaseModel):
    """Base user schema with common fields."""

    email: EmailStr = Field(..., description="User email")


class UserCreate(UserBase):
    """Schema for creating a new user from ProConnect claims."""

    proconnect_sub: str = Field(..., description="ProConnect subject ID")
    email_verified: bool = Field(default=False, description="Email verification status")
    proconnect_claims: dict[str, Any] | None = Field(
        None, description="Full ProConnect claims"
    )


class UserUpdate(BaseModel):
    """Schema for updating user information."""

    email: EmailStr | None = None
    email_verified: bool | None = None
    is_admin: bool | None = None
    proconnect_claims: dict[str, Any] | None = None


class UserRead(UserBase):
    """Schema for reading user data."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    proconnect_sub: str
    email_verified: bool
    is_admin: bool
    created_at: datetime
    updated_at: datetime


class UserConfigurationBase(BaseModel):
    """Base configuration schema."""

    name: str = Field(..., description="Configuration name", max_length=255)
    feature_settings: dict[str, Any] = Field(..., description="Feature settings")
    is_default: bool = Field(default=False, description="Is default configuration")


class UserConfigurationCreate(UserConfigurationBase):
    """Schema for creating a new configuration."""

    pass


class UserConfigurationUpdate(BaseModel):
    """Schema for updating a configuration."""

    name: str | None = None
    feature_settings: dict[str, Any] | None = None
    is_default: bool | None = None


class UserConfigurationRead(UserConfigurationBase):
    """Schema for reading configuration data."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class ProcessingJobBase(BaseModel):
    """Base processing job schema."""

    status: str = Field(..., description="Job status")
    percent: int = Field(default=0, ge=0, le=100, description="Progress percentage")
    message: str | None = Field(None, description="Status message")


class ProcessingJobCreate(BaseModel):
    """Schema for creating a new processing job."""

    input_file_s3_path: str = Field(..., description="Input file S3 path")
    config_file_used: str = Field(..., description="Config file path")
    feature_config: dict[str, Any] = Field(
        ..., description="Feature configuration snapshot"
    )
    timeout_minutes: int = Field(default=60, ge=1, description="Timeout in minutes")


class ProcessingJobUpdate(BaseModel):
    """Schema for updating a processing job."""

    status: str | None = None
    percent: int | None = Field(None, ge=0, le=100)
    message: str | None = None
    output_file_s3_path: str | None = None
    error_details: dict[str, Any] | None = None
    completed_at: datetime | None = None


class ProcessingJobRead(ProcessingJobBase):
    """Schema for reading processing job data."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    input_file_s3_path: str
    output_file_s3_path: str | None
    config_file_used: str
    feature_config: dict[str, Any]
    error_details: dict[str, Any] | None
    started_at: datetime
    updated_at: datetime
    completed_at: datetime | None
    timeout_minutes: int


class SimilarityDBManifestBase(BaseModel):
    """Base similarity database manifest schema."""

    name: str = Field(..., description="Database name", max_length=255)
    s3_folder_path: str = Field(..., description="S3 folder path")
    s3_file_path: str = Field(..., description="Full S3 file path")
    size_bytes: int = Field(..., ge=0, description="File size in bytes")
    row_count: int | None = Field(None, ge=0, description="Number of rows")
    db_metadata: dict[str, Any] | None = Field(None, description="Additional metadata")
    input_files: dict[str, Any] | None = Field(
        None,
        description="List of input files (replaces S3 manifest system)",
    )


class SimilarityDBManifestCreate(SimilarityDBManifestBase):
    """Schema for creating a new similarity database manifest."""

    last_modified: datetime = Field(..., description="S3 file last modified time")


class SimilarityDBManifestUpdate(BaseModel):
    """Schema for updating a similarity database manifest."""

    name: str | None = None
    size_bytes: int | None = Field(None, ge=0)
    row_count: int | None = Field(None, ge=0)
    last_modified: datetime | None = None
    db_metadata: dict[str, Any] | None = None
    input_files: dict[str, Any] | None = None
    is_active: bool | None = None


class SimilarityDBManifestRead(SimilarityDBManifestBase):
    """Schema for reading similarity database manifest data."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_by_user_id: uuid.UUID
    last_modified: datetime
    is_active: bool
    created_at: datetime


class OAuthAuthRequestRead(BaseModel):
    """Schema for inspecting OAuth state records (mostly for tests/debug)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    state: str
    code_verifier: str
    created_at: datetime
    ip_address: str | None = None
    user_agent: str | None = None
