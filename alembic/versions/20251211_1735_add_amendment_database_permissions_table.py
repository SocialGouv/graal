"""Add amendment_database_permissions table

Revision ID: 20251211_1735
Revises: 20251209_0003_dfb8a3c40e7f
Create Date: 2025-12-11 17:35:00
"""

import sqlalchemy as sa

from alembic import op

# Revision identifiers, used by Alembic.
revision = "20251211_1735"
down_revision = "20251209_0003_dfb8a3c40e7f"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "amendment_database_permissions",
        sa.Column(
            "db_id",
            sa.UUID(),
            sa.ForeignKey("similarity_db_manifests.id", ondelete="CASCADE"),
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
            sa.Enum("owner", "writer", "reader", name="dbrole"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("db_id", "user_id"),
    )


def downgrade():
    op.drop_table("amendment_database_permissions")
    op.execute("DROP TYPE dbrole")
