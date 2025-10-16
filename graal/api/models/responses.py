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
