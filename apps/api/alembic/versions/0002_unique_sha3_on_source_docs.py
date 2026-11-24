"""Unique index on rules.source_docs.sha3_256, so a file is stored once.

Revision ID: 0002
Revises: 0001
"""
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_source_docs_sha3_256", "source_docs", ["sha3_256"], unique=True, schema="rules"
    )


def downgrade() -> None:
    op.drop_index("ix_source_docs_sha3_256", table_name="source_docs", schema="rules")
