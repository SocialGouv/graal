"""rename_metadata_to_db_metadata

Revision ID: 68fe6d0fd15e
Revises: 001_initial_schema
Create Date: 2025-11-26 18:45:57.779378

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "68fe6d0fd15e"
down_revision: Union[str, None] = "001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Rename 'metadata' column to 'db_metadata' in similarity_db_manifests table."""
    op.alter_column(
        "similarity_db_manifests",
        "metadata",
        new_column_name="db_metadata",
    )


def downgrade() -> None:
    """Rename 'db_metadata' column back to 'metadata' in similarity_db_manifests table."""
    op.alter_column(
        "similarity_db_manifests",
        "db_metadata",
        new_column_name="metadata",
    )
