"""remove_s3_config_file_path_from_user_configurations

Revision ID: dfb8a3c40e7f
Revises: f96ecfde67e6
Create Date: 2025-12-09 00:03:41.703401

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "dfb8a3c40e7f"
down_revision: Union[str, None] = "f96ecfde67e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Remove s3_config_file_path column from user_configurations table."""
    op.drop_column("user_configurations", "s3_config_file_path")


def downgrade() -> None:
    """Add back s3_config_file_path column if downgrading."""
    op.add_column(
        "user_configurations",
        sa.Column("s3_config_file_path", sa.String(length=512), nullable=True),
    )
    # Note: Column will be nullable after downgrade as we can't restore the original values
