"""Add trigram index on user email for faster search

Revision ID: add_email_trgm_2025_12_17
Revises: add_amdt_db_perms_2025_12_15
Create Date: 2025-12-17 17:00:00
"""

from typing import Union

from alembic import op

# Revision identifiers, used by Alembic.
revision = "add_email_trgm_2025_12_17"
down_revision: Union[str, None] = "add_amdt_db_perms_2025_12_15"
branch_labels = None
depends_on = None


def upgrade():
    # Enable pg_trgm extension for trigram-based text search
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    # Create GIN index on email using trigram operator class for fast ILIKE searches
    # This index will be used for partial/fuzzy matching like "email ILIKE '%search%'"
    op.execute(
        "CREATE INDEX ix_users_email_trgm ON users USING GIN (email gin_trgm_ops)"
    )


def downgrade():
    # Drop the trigram index
    op.execute("DROP INDEX IF EXISTS ix_users_email_trgm")

    # Note: We don't drop the pg_trgm extension in downgrade as it might be used
    # by other parts of the system. Extensions are typically kept once created.
