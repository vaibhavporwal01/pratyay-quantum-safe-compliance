"""identity.users, and the maker-checker rule workflow on rules.rules.

identity.users is owned by Vishnukant (docs/contracts.md); it starts with the columns the dev
role stand-in needs. rules.rules gets typed templates, the quoted paragraph, related
paragraphs and the draft / approved / rejected / retired workflow.

Revision ID: 0003
Revises: 0002
"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

S = "rules"
STATUSES = "('draft', 'approved', 'rejected', 'retired')"
TEMPLATES = (
    "('max_amount', 'max_ratio', 'min_days', 'time_window', 'prohibited_charge', "
    "'required_disclosure')"
)
ROLES = "('borrower', 'officer', 'maker', 'checker', 'auditor', 'admin')"


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS identity")
    op.create_table(
        "users",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(f"role IN {ROLES}", name=op.f("ck_users_role")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("email", name=op.f("uq_users_email")),
        schema="identity",
    )

    op.add_column("source_docs", sa.Column("pages", sa.Integer(), nullable=True), schema=S)

    # rules.rules: P1 rows (if any) were placeholders with no workflow, so the old status
    # values map onto the new ones.
    op.drop_constraint("ck_rules_status", "rules", schema=S)
    op.drop_constraint("ck_rules_effective_range", "rules", schema=S)
    op.execute(
        "UPDATE rules.rules SET status = CASE status WHEN 'active' THEN 'approved' "
        "ELSE 'retired' END"
    )
    op.alter_column("rules", "status", server_default=sa.text("'draft'"), schema=S)
    op.alter_column("rules", "rule_set_id", nullable=True, schema=S)
    op.alter_column("rules", "effective_from", nullable=True, schema=S)
    op.alter_column("rules", "body", new_column_name="params", schema=S)
    op.alter_column("rules", "drafted_by", new_column_name="made_by", schema=S)
    op.alter_column("rules", "approved_by", new_column_name="checked_by", schema=S)
    op.execute("UPDATE rules.rules SET made_by = gen_random_uuid() WHERE made_by IS NULL")
    op.alter_column("rules", "made_by", nullable=False, schema=S)

    op.alter_column("rules", "applies_to", server_default=None, schema=S)
    op.alter_column(
        "rules", "applies_to", type_=sa.Text(), server_default=sa.text("'all'"),
        postgresql_using="COALESCE(applies_to->>'segment', 'all')", schema=S,
    )
    op.add_column(
        "rules", sa.Column("template", sa.Text(), server_default="required_disclosure",
                           nullable=False), schema=S,
    )
    op.alter_column("rules", "template", server_default=None, schema=S)
    op.add_column(
        "rules", sa.Column("para_text", sa.Text(), server_default="", nullable=False), schema=S
    )
    op.alter_column("rules", "para_text", server_default=None, schema=S)
    op.add_column(
        "rules",
        sa.Column("related", postgresql.JSONB(astext_type=sa.Text()),
                  server_default=sa.text("'[]'::jsonb"), nullable=False),
        schema=S,
    )
    op.add_column("rules", sa.Column("review_note", sa.Text(), nullable=True), schema=S)
    for col in ("created_at", "updated_at"):
        op.add_column(
            "rules",
            sa.Column(col, sa.DateTime(timezone=True), server_default=sa.func.now(),
                      nullable=False),
            schema=S,
        )
    op.add_column(
        "rules", sa.Column("checked_at", sa.DateTime(timezone=True), nullable=True), schema=S
    )

    op.create_check_constraint(
        op.f("ck_rules_status"), "rules", f"status IN {STATUSES}", schema=S)
    op.create_check_constraint(
        op.f("ck_rules_template"), "rules", f"template IN {TEMPLATES}", schema=S)
    op.create_check_constraint(
        op.f("ck_rules_applies_to"), "rules", "applies_to IN ('microfinance', 'all')", schema=S
    )
    op.create_check_constraint(
        op.f("ck_rules_effective_range"), "rules",
        "effective_to IS NULL OR effective_from IS NULL OR effective_to >= effective_from",
        schema=S,
    )
    op.create_check_constraint(
        op.f("ck_rules_maker_checker"), "rules", "checked_by IS NULL OR checked_by <> made_by", schema=S
    )
    op.create_index("ix_rules_status", "rules", ["status"], schema=S)


def downgrade() -> None:
    op.drop_index("ix_rules_status", table_name="rules", schema=S)
    for name in ("maker_checker", "effective_range", "applies_to", "template", "status"):
        op.drop_constraint(f"ck_rules_{name}", "rules", schema=S)
    for col in ("checked_at", "updated_at", "created_at", "review_note", "related",
                "para_text", "template"):
        op.drop_column("rules", col, schema=S)
    op.alter_column("rules", "applies_to", server_default=None, schema=S)
    op.alter_column(
        "rules", "applies_to", type_=postgresql.JSONB(astext_type=sa.Text()),
        server_default=sa.text("'{}'::jsonb"),
        postgresql_using="jsonb_build_object('segment', applies_to)", schema=S,
    )
    op.alter_column("rules", "made_by", nullable=True, new_column_name="drafted_by", schema=S)
    op.alter_column("rules", "checked_by", new_column_name="approved_by", schema=S)
    op.alter_column("rules", "params", new_column_name="body", schema=S)
    op.execute("DELETE FROM rules.rules WHERE rule_set_id IS NULL OR effective_from IS NULL")
    op.alter_column("rules", "effective_from", nullable=False, schema=S)
    op.alter_column("rules", "rule_set_id", nullable=False, schema=S)
    op.execute(
        "UPDATE rules.rules SET status = CASE status WHEN 'approved' THEN 'active' "
        "ELSE 'repealed' END"
    )
    op.alter_column("rules", "status", server_default=sa.text("'active'"), schema=S)
    op.create_check_constraint(
        op.f("ck_rules_status"), "rules", "status IN ('active', 'superseded', 'repealed')", schema=S
    )
    op.create_check_constraint(
        op.f("ck_rules_effective_range"), "rules", "effective_to IS NULL OR effective_to >= effective_from",
        schema=S,
    )
    op.drop_column("source_docs", "pages", schema=S)
    op.drop_table("users", schema="identity")
    op.execute("DROP SCHEMA IF EXISTS identity")
