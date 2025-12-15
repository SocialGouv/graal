"""
Database Permission Service

Manages per-database user roles (owner, writer, reader) stored in
the amendment_database_permissions table.

Responsibilities:
- Retrieve a user's role for a DB
- Assign/update/remove roles
- Enforce "at least one remaining owner" rule
- List all roles for a DB
- List all DBs a user can access

Pattern:
- Async database access
- Singleton factory function
- No business logic leakage into API layer
"""

import logging
import logging.config
from typing import Optional

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from graal.database.models import AmendmentDatabasePermission, DbRoleEnum

logging.config.fileConfig("logging.conf")


class DbRole:
    """Convenience wrapper for database roles.

    Exposes enum members for external callers (e.g. routes) while providing
    an ordering via the RANK mapping for hierarchical permission checks.
    """

    owner = DbRoleEnum.owner
    writer = DbRoleEnum.writer
    reader = DbRoleEnum.reader

    RANK = {
        reader: 1,
        writer: 2,
        owner: 3,
    }


class DatabasePermissionService:
    """Service for managing amendment database permissions."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self._session_factory = session_factory
        logging.info("[DatabasePermissionService] Initialized")

    async def get_user_role(self, db_id: str, user_id: str) -> Optional[DbRoleEnum]:
        """Return the user's role for a specific database."""
        async with self._session_factory() as session:
            result = await session.execute(
                select(AmendmentDatabasePermission.role).where(
                    AmendmentDatabasePermission.db_id == db_id,
                    AmendmentDatabasePermission.user_id == user_id,
                )
            )
            return result.scalar_one_or_none()

    async def list_roles_for_db(self, db_id: str) -> list[AmendmentDatabasePermission]:
        """Return the full permission list for a DB."""
        async with self._session_factory() as session:
            result = await session.execute(
                select(AmendmentDatabasePermission).where(
                    AmendmentDatabasePermission.db_id == db_id
                )
            )
            return list(result.scalars().all())

    async def list_accessible_databases(self, user_id: str) -> list[str]:
        """List the DB IDs where the user has at least reader permissions."""
        async with self._session_factory() as session:
            result = await session.execute(
                select(AmendmentDatabasePermission.db_id).where(
                    AmendmentDatabasePermission.user_id == user_id
                )
            )
            return [row[0] for row in result.all()]

    async def _count_owners(self, session: AsyncSession, db_id: str) -> int:
        """Count current owners (internal helper)."""
        result = await session.execute(
            select(AmendmentDatabasePermission).where(
                AmendmentDatabasePermission.db_id == db_id,
                AmendmentDatabasePermission.role == DbRole.owner,
            )
        )
        return len(result.scalars().all())

    async def set_user_role(
        self, db_id: str, target_user_id: str, role: DbRoleEnum | str
    ) -> None:
        """Set or update a user's role for a DB.

        The ``role`` parameter may be provided either as a ``DbRoleEnum`` member
        or as its corresponding string value ("owner", "writer", "reader").
        """
        # Normalise to enum instance for consistent storage and comparison
        role_enum = DbRoleEnum(role)

        async with self._session_factory() as session:
            # Check if the user already has a role
            result = await session.execute(
                select(AmendmentDatabasePermission).where(
                    AmendmentDatabasePermission.db_id == db_id,
                    AmendmentDatabasePermission.user_id == target_user_id,
                )
            )
            existing = result.scalar_one_or_none()

            if existing:
                # Handle owner demotion: ensure at least one owner remains
                if (
                    existing.role == DbRole.owner
                    and role_enum != DbRole.owner
                    and await self._count_owners(session, db_id) <= 1
                ):
                    raise ValueError(
                        "Cannot demote the last remaining owner of this database"
                    )

                existing.role = role_enum
            else:
                # Create new role entry
                new_perm = AmendmentDatabasePermission(
                    db_id=db_id,
                    user_id=target_user_id,
                    role=role_enum,
                )
                session.add(new_perm)

            await session.commit()

    async def remove_user_role(self, db_id: str, target_user_id: str) -> None:
        """Remove a user's role on a DB (owner-only operation)."""
        async with self._session_factory() as session:
            # Check current role
            result = await session.execute(
                select(AmendmentDatabasePermission).where(
                    AmendmentDatabasePermission.db_id == db_id,
                    AmendmentDatabasePermission.user_id == target_user_id,
                )
            )
            existing = result.scalar_one_or_none()

            if not existing:
                return  # Nothing to remove

            # Prevent removing the last owner
            if (
                existing.role == DbRole.owner
                and await self._count_owners(session, db_id) <= 1
            ):
                raise ValueError(
                    "Cannot remove owner role: at least one owner is required"
                )

            await session.execute(
                delete(AmendmentDatabasePermission).where(
                    AmendmentDatabasePermission.db_id == db_id,
                    AmendmentDatabasePermission.user_id == target_user_id,
                )
            )
            await session.commit()


# Singleton instance
_database_permission_service: Optional[DatabasePermissionService] = None


def get_database_permission_service() -> DatabasePermissionService:
    """Get global DatabasePermissionService instance."""
    global _database_permission_service
    if _database_permission_service is None:
        logging.info("[DatabasePermissionService] Initializing singleton instance")
        from graal.database.base import get_async_session_maker

        session_factory = get_async_session_maker()
        _database_permission_service = DatabasePermissionService(session_factory)

    return _database_permission_service
