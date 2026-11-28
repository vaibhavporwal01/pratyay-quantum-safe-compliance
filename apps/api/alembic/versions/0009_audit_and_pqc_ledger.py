"""Persistent encrypted audit events and ML-DSA signed hash-chain ledger."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0009_audit_pqc_ledger"
down_revision = "0008"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS audit")
    op.execute("CREATE SCHEMA IF NOT EXISTS trust")
    op.create_table(
        "events",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("target", sa.Text(), nullable=False),
        sa.Column("meta_ciphertext", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        schema="audit")
    op.create_index("ix_audit_events_actor_id", "events", ["actor_id"], schema="audit")
    op.create_index("ix_audit_events_action", "events", ["action"], schema="audit")
    op.create_index("ix_audit_events_created_at", "events", ["created_at"], schema="audit")
    op.create_table(
        "ledger_entries",
        sa.Column("seq", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False, unique=True),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("previous_hash", sa.LargeBinary(), nullable=False),
        sa.Column("entry_hash", sa.LargeBinary(), nullable=False, unique=True),
        sa.Column("signature", sa.LargeBinary(), nullable=False),
        sa.Column("key_id", sa.Text(), nullable=False),
        sa.Column("algorithm", sa.Text(), server_default="ML-DSA-65", nullable=False),
        sa.Column("public_key", sa.LargeBinary(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        schema="trust")

def downgrade() -> None:
    op.drop_table("ledger_entries", schema="trust")
    op.drop_table("events", schema="audit")
    op.execute("DROP SCHEMA IF EXISTS trust")
    op.execute("DROP SCHEMA IF EXISTS audit")
