"""add llm configs

Revision ID: 22dc66ee7610
Revises: 252c331e76a3
Create Date: 2026-02-27 00:17:52.643422

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "22dc66ee7610"
down_revision: Union[str, None] = "252c331e76a3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "llm_configs",
        sa.Column("id", sa.UUID(), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column(
            "provider",
            sa.Enum(
                "albert",
                name="llmprovider",
            ),
            nullable=False,
        ),
        sa.Column("model_name", sa.String(length=255), nullable=False),
        sa.Column("base_url", sa.String(length=512), nullable=True),
        sa.Column("api_key", sa.Text(), nullable=True),
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
        sa.UniqueConstraint("name", name="uq_llm_configs_name"),
    )

    op.create_index("ix_llm_configs_name", "llm_configs", ["name"], unique=True)
    op.create_index("ix_llm_configs_provider", "llm_configs", ["provider"])


def downgrade() -> None:
    op.drop_index("ix_llm_configs_provider", table_name="llm_configs")
    op.drop_index("ix_llm_configs_name", table_name="llm_configs")
    op.drop_table("llm_configs")
    op.execute("DROP TYPE llmprovider")
