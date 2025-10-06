"""
API request models.
"""

import re

from pydantic import BaseModel, Field, field_validator


class ProcessingConfig(BaseModel):
    """Configuration model for processing parameters."""

    origin_project: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Name of the legislative project (e.g., 'PLFSS 2025')",
    )

    # Future configuration fields will be added here:
    # processing_date: Optional[str] = Field(None, description="Custom processing date")
    # enabled_features: Optional[List[str]] = Field(None, description="List of enabled features")
    # custom_thresholds: Optional[Dict[str, float]] = Field(None, description="Custom similarity thresholds")

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


class ProcessingRequest(BaseModel):
    """Request model for processing amendments."""

    processing_config: ProcessingConfig = Field(
        ..., description="Processing configuration parameters"
    )
