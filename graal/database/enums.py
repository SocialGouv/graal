"""Database-related enumerations.

This module intentionally contains lightweight Enum definitions that can be
imported by both SQLAlchemy ORM models and FastAPI/Pydantic models.

Keeping these enums in a dedicated module avoids importing the full SQLAlchemy
model module from API schemas, and helps ensure OpenAPI stays in sync with the
backend source of truth.
"""

from __future__ import annotations

import enum


class DbRoleEnum(str, enum.Enum):
    """Roles for amendment database permissions."""

    owner = "owner"
    writer = "writer"
    reader = "reader"
