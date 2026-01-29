"""add excel config manifests

Revision ID: 252c331e76a3
Revises: 509f4958dc7d
Create Date: 2026-01-29 18:04:57.949789

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "252c331e76a3"
down_revision: Union[str, None] = "509f4958dc7d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "excel_config_manifests",
        sa.Column("id", sa.UUID(), primary_key=True, nullable=False),
        sa.Column(
            "owner_user_id",
            sa.UUID(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("s3_key", sa.String(length=512), unique=True, nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("sheet_metadata", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "deleted_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Soft delete timestamp",
        ),
    )

    op.create_table(
        "excel_config_permissions",
        sa.Column(
            "config_id",
            sa.UUID(),
            sa.ForeignKey("excel_config_manifests.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.UUID(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "role",
            # Keep this enum in sync with ExcelConfigRoleEnum. Any changes to the
            # enum values require a dedicated migration to alter the DB type.
            sa.Enum("owner", "reader", name="excelconfigrole"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("config_id", "user_id"),
    )

    op.create_index(
        "ix_excel_config_permissions_user",
        "excel_config_permissions",
        ["user_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_excel_config_permissions_user", table_name="excel_config_permissions"
    )
    op.drop_table("excel_config_permissions")
    op.execute("DROP TYPE excelconfigrole")

    op.drop_table("excel_config_manifests")
