"""Initial database schema

Revision ID: 001_initial_schema
Revises:
Create Date: 2025-11-20 14:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create all initial tables and indexes."""

    # Create PostgreSQL function for auto-updating updated_at timestamps
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = now();
            RETURN NEW;
        END;
        $$ language 'plpgsql';
    """)

    # Create users table
    op.create_table(
        "users",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment="Unique user identifier",
        ),
        sa.Column(
            "proconnect_sub",
            sa.String(length=255),
            nullable=False,
            comment="ProConnect subject ID (unique identifier from ProConnect)",
        ),
        sa.Column(
            "email",
            sa.String(length=255),
            nullable=False,
            comment="User email from ProConnect",
        ),
        sa.Column(
            "email_verified",
            sa.Boolean(),
            nullable=False,
            server_default="false",
            comment="Email verification status from ProConnect",
        ),
        sa.Column(
            "is_admin",
            sa.Boolean(),
            nullable=False,
            server_default="false",
            comment="Admin permission flag (managed internally)",
        ),
        sa.Column(
            "proconnect_claims",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="Full ProConnect claims for audit/debugging",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
            comment="Account creation timestamp",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
            comment="Last update timestamp",
        ),
        sa.Column(
            "last_login",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Last successful login timestamp",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.UniqueConstraint("proconnect_sub", name="uq_users_proconnect_sub"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index("ix_users_proconnect_sub", "users", ["proconnect_sub"])
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_users_is_admin", "users", ["is_admin"])

    # Create trigger for updated_at on users
    op.execute("""
        CREATE TRIGGER update_users_updated_at
        BEFORE UPDATE ON users
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
    """)

    # Create user_configurations table
    op.create_table(
        "user_configurations",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment="Configuration identifier",
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment="Owner user ID",
        ),
        sa.Column(
            "name", sa.String(length=255), nullable=False, comment="Configuration name"
        ),
        sa.Column(
            "s3_config_file_path",
            sa.String(length=512),
            nullable=False,
            comment="Path to config file in S3",
        ),
        sa.Column(
            "feature_settings",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            comment="Feature toggles and parameters",
        ),
        sa.Column(
            "is_default",
            sa.Boolean(),
            nullable=False,
            server_default="false",
            comment="Whether this is the user's default configuration",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
            comment="Creation timestamp",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
            comment="Last update timestamp",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_user_configurations_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_user_configurations"),
    )
    op.create_index(
        "ix_user_configurations_user_id", "user_configurations", ["user_id"]
    )
    op.create_index(
        "ix_user_configs_user_default", "user_configurations", ["user_id", "is_default"]
    )

    # Create trigger for updated_at on user_configurations
    op.execute("""
        CREATE TRIGGER update_user_configurations_updated_at
        BEFORE UPDATE ON user_configurations
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
    """)

    # Create similarity_db_manifests table
    op.create_table(
        "similarity_db_manifests",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment="Manifest identifier",
        ),
        sa.Column(
            "created_by_user_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment="Creator user ID",
        ),
        sa.Column(
            "name",
            sa.String(length=255),
            nullable=False,
            comment="Database friendly name",
        ),
        sa.Column(
            "s3_folder_path",
            sa.String(length=512),
            nullable=False,
            comment="S3 folder path (e.g., PLFSS/)",
        ),
        sa.Column(
            "s3_file_path",
            sa.String(length=512),
            nullable=False,
            comment="Full S3 path to parquet file",
        ),
        sa.Column(
            "size_bytes", sa.BigInteger(), nullable=False, comment="File size in bytes"
        ),
        sa.Column(
            "row_count",
            sa.Integer(),
            nullable=True,
            comment="Number of rows in database",
        ),
        sa.Column(
            "last_modified",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="S3 file last modified time",
        ),
        sa.Column(
            "db_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="Additional db_metadata (project, year, etc.)",
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default="true",
            comment="Whether database is active/available",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
            comment="Manifest creation time",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            name="fk_similarity_db_manifests_created_by_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_similarity_db_manifests"),
        sa.UniqueConstraint(
            "s3_file_path", name="uq_similarity_db_manifests_s3_file_path"
        ),
    )
    op.create_index(
        "ix_similarity_db_manifests_is_active", "similarity_db_manifests", ["is_active"]
    )
    op.create_index(
        "ix_similarity_db_manifests_s3_file_path",
        "similarity_db_manifests",
        ["s3_file_path"],
    )


def downgrade() -> None:
    """Drop all tables and indexes."""

    # Drop similarity_db_manifests
    op.drop_index(
        "ix_similarity_db_manifests_s3_file_path", table_name="similarity_db_manifests"
    )
    op.drop_index(
        "ix_similarity_db_manifests_is_active", table_name="similarity_db_manifests"
    )
    op.drop_table("similarity_db_manifests")

    # Drop user_configurations
    op.execute(
        "DROP TRIGGER IF EXISTS update_user_configurations_updated_at ON user_configurations;"
    )
    op.drop_index("ix_user_configs_user_default", table_name="user_configurations")
    op.drop_index("ix_user_configurations_user_id", table_name="user_configurations")
    op.drop_table("user_configurations")

    # Drop users
    op.execute("DROP TRIGGER IF EXISTS update_users_updated_at ON users;")
    op.drop_index("ix_users_is_admin", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_index("ix_users_proconnect_sub", table_name="users")
    op.drop_table("users")

    # Drop the update_updated_at_column function
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column() CASCADE;")
