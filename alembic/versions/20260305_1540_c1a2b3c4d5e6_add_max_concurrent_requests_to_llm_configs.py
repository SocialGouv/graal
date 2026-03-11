"""add max_concurrent_requests to llm_configs

Revision ID: c1a2b3c4d5e6
Revises: ab36e72df6a7
Create Date: 2026-03-05 15:40:00.000000

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c1a2b3c4d5e6"
down_revision: Union[str, None] = "ab36e72df6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "llm_configs",
        sa.Column(
            "max_concurrent_requests",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("6"),
        ),
    )


def downgrade() -> None:
    op.drop_column("llm_configs", "max_concurrent_requests")
