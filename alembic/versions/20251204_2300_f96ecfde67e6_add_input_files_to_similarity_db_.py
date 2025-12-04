"""add_input_files_to_similarity_db_manifests

Revision ID: f96ecfde67e6
Revises: 001_initial_schema
Create Date: 2025-12-04 23:00:23.247675

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f96ecfde67e6"
down_revision: Union[str, None] = "001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add input_files column to similarity_db_manifests table
    op.add_column(
        "similarity_db_manifests",
        sa.Column(
            "input_files",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="List of input files used to build this database (file_hash, filename, s3_key, uploaded_at, metadata)",
        ),
    )


def downgrade() -> None:
    # Remove input_files column from similarity_db_manifests table
    op.drop_column("similarity_db_manifests", "input_files")
