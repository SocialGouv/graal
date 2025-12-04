"""
API response models.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    """Job processing status enumeration."""

    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"
    timeout = "timeout"


class ProcessingResponse(BaseModel):
    """Response model for processing job creation."""

    job_id: str
    status: JobStatus
    message: str


class ProgressResponse(BaseModel):
    """Response model for job progress status."""

    job_id: str
    status: JobStatus
    percent: int  # 0-100
    message: Optional[str] = None
    started_at: datetime
    updated_at: datetime


class AmendmentPreview(BaseModel):
    """Model for a single amendment in preview results."""

    num_amdt: Optional[str] = None
    commentaires: Optional[str] = None
    allotissement: Optional[str] = None
    objet_amdt: Optional[str] = None
    sort: Optional[str] = None
    reponse: Optional[str] = None
    affectation_email: Optional[str] = None
    affectation_nom: Optional[str] = None
    entite_pilote: Optional[str] = None
    avis_du_gouvernement: Optional[str] = None
    groupe: Optional[str] = None
    num_article: Optional[str] = None
    expose_amdt: Optional[str] = None
    corps_amdt: Optional[str] = None
    mission: Optional[str] = None


class PreviewResponse(BaseModel):
    """Response model for results preview."""

    job_id: str
    total_rows: int
    preview_rows: List[AmendmentPreview]
    columns: List[str]


class ConfigFilesResponse(BaseModel):
    """Response model for available configuration files."""

    files: List[str] = Field(description="List of available configuration file names")
    total: int = Field(description="Total number of available files")


class ErrorResponse(BaseModel):
    """Response model for API errors."""

    error: str
    message: str
    details: Optional[Dict[str, Any]] = None


class DatabaseInfo(BaseModel):
    """Information about a similarity database."""

    name: str = Field(..., description="Database name (without extension)")
    size_bytes: int = Field(..., description="File size in bytes")
    last_modified: datetime = Field(..., description="Last modification timestamp")


class DatabaseListResponse(BaseModel):
    """Response containing list of available databases."""

    databases: list[DatabaseInfo] = Field(..., description="List of databases")
    total: int = Field(..., description="Total number of databases")


class FileUploadResponse(BaseModel):
    """Response model for file upload."""

    upload_id: str = Field(..., description="Unique upload identifier")
    filename: str = Field(..., description="Original filename")
    file_hash: str = Field(..., description="SHA256 hash of file content")
    s3_key: str = Field(..., description="S3 key where file is stored in pool")
    already_existed: bool = Field(
        ..., description="True if file already existed in pool (deduplicated)"
    )
    size: int = Field(..., description="File size in bytes")
    metadata: dict[str, Any] = Field(..., description="Processing metadata")


class FileReferenceInfo(BaseModel):
    """Information about a file in a database manifest."""

    upload_id: str = Field(
        ..., description="Upload ID (derived from hash for UI compatibility)"
    )
    filename: str = Field(..., description="Original filename provided by user")
    file_hash: str = Field(..., description="SHA256 hash of file content")
    s3_key: str = Field(..., description="S3 key in pool")
    uploaded_at: str = Field(
        ..., description="ISO 8601 timestamp when file was uploaded"
    )
    metadata: dict[str, Any] = Field(..., description="Processing metadata")


class DatabaseManifestResponse(BaseModel):
    """Response model for database manifest."""

    database_name: str = Field(..., description="Name of the database")
    created_at: str = Field(
        ..., description="ISO 8601 timestamp when database was created"
    )
    last_updated_at: str = Field(
        ..., description="ISO 8601 timestamp when database was last updated"
    )
    files: list[FileReferenceInfo] = Field(..., description="List of files in database")
    total_files: int = Field(..., description="Total number of files")


class UserResponse(BaseModel):
    """Response model for user information.

    This response includes the is_admin field, making it the single source
    for both user information and admin status checks.
    """

    user_id: str = Field(..., description="Unique user identifier")
    email: Optional[str] = Field(None, description="User email address")
    is_admin: bool = Field(..., description="Whether user has admin privileges")
