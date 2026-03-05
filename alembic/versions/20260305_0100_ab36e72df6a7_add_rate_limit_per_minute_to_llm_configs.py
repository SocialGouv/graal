"""add rate_limit_per_minute to llm_configs

Revision ID: ab36e72df6a7
Revises: 22dc66ee7610
Create Date: 2026-03-05 01:00:01.048250

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ab36e72df6a7"
down_revision: Union[str, None] = "22dc66ee7610"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "llm_configs",
        sa.Column(
            "rate_limit_per_minute",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("500"),
        ),
    )


def downgrade() -> None:
    op.drop_column("llm_configs", "rate_limit_per_minute")
