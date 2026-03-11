"""SQLAlchemy ORM models for GRAAL database.

This module defines all database models using SQLAlchemy 2.0 declarative syntax
with full type hints and relationship mappings.
"""

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from graal.database.base import Base
from graal.database.enums import DbRoleEnum, ExcelConfigRoleEnum, LlmProviderEnum


def utc_now() -> datetime:
    """Get current UTC timestamp.

    Returns:
        Current datetime in UTC
    """
    return datetime.now(timezone.utc)


class User(Base):
    """User model for authentication via ProConnect.

    Users authenticate through ProConnect (French government identity provider)
    and their profile is created/updated from ProConnect claims on each login.
    """

    __tablename__ = "users"

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Unique user identifier",
    )

    # ProConnect fields
    proconnect_sub: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        comment="ProConnect subject ID (unique identifier from ProConnect)",
    )

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        comment="User email from ProConnect",
    )

    email_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Email verification status from ProConnect",
    )

    # Internal fields
    is_admin: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
        comment="Admin permission flag (managed internally)",
    )

    proconnect_claims: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB, nullable=True, comment="Full ProConnect claims for audit/debugging"
    )

    # Audit timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Account creation timestamp",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="Last update timestamp",
    )

    # Relationships
    configurations: Mapped[list["UserConfiguration"]] = relationship(
        "UserConfiguration", back_populates="user", cascade="all, delete-orphan"
    )

    processing_jobs: Mapped[list["ProcessingJob"]] = relationship(
        "ProcessingJob", back_populates="user", cascade="all, delete-orphan"
    )

    created_manifests: Mapped[list["SimilarityDBManifest"]] = relationship(
        "SimilarityDBManifest",
        back_populates="created_by_user",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, is_admin={self.is_admin})>"


class UserConfiguration(Base):
    """User-saved configuration presets.

    Allows users to save and reuse their preferred processing configurations.
    """

    __tablename__ = "user_configurations"

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Configuration identifier",
    )

    # Foreign key to user
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Owner user ID",
    )

    # Configuration details
    name: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="Configuration name"
    )

    feature_settings: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, comment="Feature toggles and parameters"
    )

    is_default: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether this is the user's default configuration",
    )

    # Audit timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Creation timestamp",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="Last update timestamp",
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="configurations")

    # Indexes
    __table_args__ = (Index("ix_user_configs_user_default", "user_id", "is_default"),)

    def __repr__(self) -> str:
        return f"<UserConfiguration(id={self.id}, name={self.name}, user_id={self.user_id})>"


class ProcessingJob(Base):
    """Complete history of amendment processing jobs.

    Tracks all processing jobs with their status, progress, and results.
    """

    __tablename__ = "processing_jobs"

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Job identifier",
    )

    # Foreign key to user
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Job owner user ID",
    )

    # Job status and progress
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Job status: queued, running, completed, failed, timeout",
    )

    percent: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False, comment="Progress percentage (0-100)"
    )

    message: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Status message"
    )

    # File paths
    input_file_s3_path: Mapped[str] = mapped_column(
        String(512), nullable=False, comment="Input file location in S3"
    )

    output_file_s3_path: Mapped[str | None] = mapped_column(
        String(512), nullable=True, comment="Output file location in S3"
    )

    # Configuration
    config_file_used: Mapped[str] = mapped_column(
        String(512), nullable=False, comment="Config file path used for this job"
    )

    feature_config: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, comment="Snapshot of feature configuration at runtime"
    )

    # Error details
    error_details: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB, nullable=True, comment="Error information if job failed"
    )

    # Timing
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
        comment="Job start time",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="Last update time",
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="Job completion time"
    )

    timeout_minutes: Mapped[int] = mapped_column(
        Integer, default=60, nullable=False, comment="Timeout limit in minutes"
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="processing_jobs")

    # Indexes
    __table_args__ = (
        Index("ix_processing_jobs_user_status", "user_id", "status"),
        Index(
            "ix_processing_jobs_started_desc",
            "started_at",
            postgresql_ops={"started_at": "DESC"},
        ),
    )

    def __repr__(self) -> str:
        return f"<ProcessingJob(id={self.id}, status={self.status}, user_id={self.user_id})>"


class SimilarityDBManifest(Base):
    """Metadata for similarity databases stored in S3.

    Tracks similarity database Parquet files in S3 with their metadata,
    but not the actual file contents.
    """

    __tablename__ = "similarity_db_manifests"

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Manifest identifier",
    )

    # Foreign key to user
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="Creator user ID",
    )

    # Database information
    name: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="Database friendly name"
    )

    s3_folder_path: Mapped[str] = mapped_column(
        String(512), nullable=False, comment="S3 folder path (e.g., PLFSS/)"
    )

    s3_file_path: Mapped[str] = mapped_column(
        String(512),
        unique=True,
        nullable=False,
        index=True,
        comment="Full S3 path to parquet file",
    )

    # File metadata
    size_bytes: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="File size in bytes"
    )

    row_count: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="Number of rows in database"
    )

    last_modified: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, comment="S3 file last modified time"
    )

    db_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB, nullable=True, comment="Additional metadata (project, year, etc.)"
    )

    # Input files tracking (replaces S3 manifest system)
    input_files: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="List of input files used to build this database (file_hash, filename, s3_key, uploaded_at, metadata)",
    )

    # Status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
        comment="Whether database is active/available",
    )

    # Audit timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Manifest creation time",
    )

    # Relationships
    created_by_user: Mapped["User"] = relationship(
        "User", back_populates="created_manifests"
    )

    def __repr__(self) -> str:
        return f"<SimilarityDBManifest(id={self.id}, name={self.name}, is_active={self.is_active})>"


class AmendmentDatabasePermission(Base):
    """Permission entry for a user on a specific amendment database.

    Tracks whether a user is an owner, writer, or reader of a database.
    Ensures mutual exclusivity and supports multi-owner setups.
    """

    __tablename__ = "amendment_database_permissions"

    db_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("similarity_db_manifests.id", ondelete="CASCADE"),
        primary_key=True,
        comment="Target database ID (foreign key to SimilarityDBManifest)",
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
        comment="User ID with permissions on this database",
    )

    role: Mapped[DbRoleEnum] = mapped_column(
        Enum(DbRoleEnum, name="dbrole", native_enum=True),
        nullable=False,
        comment="Permission role: owner, writer, reader",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Timestamp when permission was granted",
    )

    def __repr__(self) -> str:
        return f"<DBPerm(db_id={self.db_id}, user_id={self.user_id}, role={self.role})>"


class ExcelConfigManifest(Base):
    """Metadata for user-uploaded Excel configuration files stored in S3."""

    __tablename__ = "excel_config_manifests"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Excel config identifier",
    )

    owner_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Owner user ID",
    )

    file_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Original filename provided by the user",
    )

    s3_key: Mapped[str] = mapped_column(
        String(512),
        unique=True,
        nullable=False,
        comment="Full S3 key where the Excel file is stored",
    )

    file_size_bytes: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        comment="Size of the Excel file in bytes",
    )

    sheet_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Optional metadata about worksheets/columns",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Upload timestamp",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="Last modification timestamp",
    )

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Soft delete timestamp",
    )

    owner: Mapped["User"] = relationship("User", backref="excel_configs")

    permissions: Mapped[list["ExcelConfigPermission"]] = relationship(
        "ExcelConfigPermission",
        back_populates="config",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<ExcelConfigManifest(id={self.id}, owner={self.owner_user_id})>"


class ExcelConfigPermission(Base):
    """Role assignment for a user on a specific Excel config."""

    __tablename__ = "excel_config_permissions"

    config_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("excel_config_manifests.id", ondelete="CASCADE"),
        primary_key=True,
        comment="Excel config identifier",
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
        comment="User with access to this config",
    )

    role: Mapped[ExcelConfigRoleEnum] = mapped_column(
        Enum(ExcelConfigRoleEnum, name="excelconfigrole", native_enum=True),
        nullable=False,
        comment="Role granted to the user",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Timestamp when role was granted",
    )

    config: Mapped["ExcelConfigManifest"] = relationship(
        "ExcelConfigManifest", back_populates="permissions"
    )

    def __repr__(self) -> str:
        return f"<ExcelConfigPermission(config_id={self.config_id}, user_id={self.user_id}, role={self.role})>"


class OAuthAuthRequest(Base):
    """OAuth login request state storage for ProConnect flow."""

    __tablename__ = "oauth_auth_requests"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="OAuth auth request identifier",
    )

    state: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        comment="OAuth state parameter (PKCE)",
    )

    code_verifier: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="PKCE code verifier to redeem authorization code",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Timestamp when state was issued",
    )

    ip_address: Mapped[str | None] = mapped_column(
        String(64), nullable=True, comment="Requester IP for observability"
    )

    user_agent: Mapped[str | None] = mapped_column(
        String(512), nullable=True, comment="Requester user-agent"
    )

    def __repr__(self) -> str:
        return f"<OAuthAuthRequest(id={self.id}, state={self.state[:8]}...)>"


class LlmConfig(Base):
    """LLM configuration stored in the database.

    These configs are used by the web UI to let admins manage which LLM providers
    are available, and by the processing pipeline to instantiate clients with
    the right credentials.
    """

    __tablename__ = "llm_configs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="LLM config identifier",
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
        comment="Human-friendly name shown in the UI",
    )

    provider: Mapped[LlmProviderEnum] = mapped_column(
        Enum(LlmProviderEnum, name="llmprovider", native_enum=True),
        nullable=False,
        index=True,
        comment="LLM provider type",
    )

    model_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Model name as understood by the provider",
    )

    # OpenAI-compatible providers (scaleway/albert/mistral)
    base_url: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
        comment="Base URL for OpenAI-compatible APIs",
    )

    api_key: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="API key for OpenAI-compatible providers",
    )

    rate_limit_per_minute: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="500",
        comment="Rate limit in requests per minute",
    )

    max_concurrent_requests: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="6",
        comment="Maximum number of concurrent summary generation requests",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Creation timestamp",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="Last update timestamp",
    )

    def __repr__(self) -> str:
        return f"<LlmConfig(id={self.id}, name={self.name}, provider={self.provider})>"
