"""
API request models.
"""

import re

from pydantic import BaseModel, Field, field_validator


class ProcessingRequest(BaseModel):
    """Request model for processing amendments."""

    origin_project: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Name of the legislative project (e.g., 'PLFSS 2025')",
    )

    # Future parameters can be easily added here:
    # processing_date: Optional[str] = Field(None, description="Custom processing date")
    # user_preferences: Optional[Dict[str, Any]] = Field(None, description="User preferences")
    # feature_flags: Optional[List[str]] = Field(None, description="Enabled feature flags")

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
