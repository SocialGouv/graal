"""add oauth auth requests table

Revision ID: 509f4958dc7d
Revises: add_email_trgm_2025_12_17
Create Date: 2026-01-28 15:11:42.861876

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "509f4958dc7d"
down_revision: Union[str, None] = "add_email_trgm_2025_12_17"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "oauth_auth_requests",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("state", sa.String(length=255), nullable=False, unique=True),
        sa.Column("code_verifier", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.String(length=512), nullable=True),
    )

    op.create_index(
        "ix_oauth_auth_requests_created_at",
        "oauth_auth_requests",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_oauth_auth_requests_created_at", table_name="oauth_auth_requests")
    op.drop_index("ix_oauth_auth_requests_state", table_name="oauth_auth_requests")
    op.drop_table("oauth_auth_requests")
