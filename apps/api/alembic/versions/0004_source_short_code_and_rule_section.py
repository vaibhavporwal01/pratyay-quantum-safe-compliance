"""rules.source_docs.short_code and rules.rules.section.

short_code is the citation code shown in anchors ("CF para 51"), stored per source instead of
derived from the title. section is the heading a rule's paragraph sits under (for context,
not a quote).

Revision ID: 0004
Revises: 0003
"""
import sqlalchemy as sa

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None

S = "rules"


def upgrade() -> None:
    op.add_column("source_docs", sa.Column("short_code", sa.Text(), nullable=True), schema=S)
    op.create_unique_constraint(
        op.f("uq_source_docs_short_code"), "source_docs", ["short_code"], schema=S
    )
    op.create_check_constraint(
        op.f("ck_source_docs_short_code"),
        "source_docs",
        "short_code IS NULL OR short_code ~ '^[A-Z][A-Z0-9-]{0,11}$'",
        schema=S,
    )
    op.add_column("rules", sa.Column("section", sa.Text(), nullable=True), schema=S)


def downgrade() -> None:
    op.drop_column("rules", "section", schema=S)
    op.drop_constraint(op.f("ck_source_docs_short_code"), "source_docs", schema=S)
    op.drop_constraint(op.f("uq_source_docs_short_code"), "source_docs", schema=S)
    op.drop_column("source_docs", "short_code", schema=S)
