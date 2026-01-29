"""Shared API type aliases.

Keep lightweight shared types here to avoid circular imports between
routes, services, and dependencies.
"""

from typing import Annotated
from uuid import UUID

ExcelConfigId = Annotated[UUID, ...]
