"""P1 schema: rules, origination and decision.

Revision ID: 0001
Revises: none
"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = '0001'
down_revision = None
branch_labels = None
depends_on = None

SCHEMAS = ("rules", "origination", "decision")


def upgrade() -> None:
    for schema in SCHEMAS:
        op.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")

    op.create_table('applications',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('org_id', sa.UUID(), nullable=False),
    sa.Column('borrower_id', sa.UUID(), nullable=False),
    sa.Column('facts', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
    sa.Column('amount_paise', sa.BigInteger(), nullable=False),
    sa.Column('tenure_months', sa.Integer(), nullable=False),
    sa.Column('status', sa.Text(), nullable=False),
    sa.Column('created_by', sa.UUID(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_applications')),
    schema='origination'
    )
    op.create_index('ix_applications_org_status_created', 'applications', ['org_id', 'status', 'created_at'], unique=False, schema='origination')
    op.create_table('rule_sets',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('org_id', sa.UUID(), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.Column('status', sa.Text(), server_default=sa.text("'draft'"), nullable=False),
    sa.Column('published_by', sa.UUID(), nullable=True),
    sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('ledger_seq', sa.BigInteger(), nullable=True),
    sa.CheckConstraint("status IN ('draft', 'published')", name=op.f('ck_rule_sets_status')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_rule_sets')),
    sa.UniqueConstraint('org_id', 'version', name=op.f('uq_rule_sets_org_id_version')),
    schema='rules'
    )
    op.create_table('source_docs',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('title', sa.Text(), nullable=False),
    sa.Column('ref_no', sa.Text(), nullable=True),
    sa.Column('issued_on', sa.Date(), nullable=True),
    sa.Column('url', sa.Text(), nullable=True),
    sa.Column('file', sa.LargeBinary(), nullable=True),
    sa.Column('sha3_256', sa.LargeBinary(), nullable=True),
    sa.Column('uploaded_by', sa.UUID(), nullable=True),
    sa.Column('uploaded_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_source_docs')),
    schema='rules'
    )
    op.create_table('decisions',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('application_id', sa.UUID(), nullable=False),
    sa.Column('rule_set_id', sa.UUID(), nullable=False),
    sa.Column('outcome', sa.Text(), nullable=False),
    sa.Column('offered_paise', sa.BigInteger(), nullable=True),
    sa.Column('maker_id', sa.UUID(), nullable=False),
    sa.Column('checker_id', sa.UUID(), nullable=True),
    sa.Column('ledger_seq', sa.BigInteger(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("outcome IN ('pass', 'refer', 'fail')", name=op.f('ck_decisions_outcome')),
    sa.CheckConstraint('checker_id IS NULL OR checker_id <> maker_id', name=op.f('ck_decisions_maker_checker')),
    sa.ForeignKeyConstraint(['application_id'], ['origination.applications.id'], name=op.f('fk_decisions_application_id_applications')),
    sa.ForeignKeyConstraint(['rule_set_id'], ['rules.rule_sets.id'], name=op.f('fk_decisions_rule_set_id_rule_sets')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_decisions')),
    schema='decision'
    )
    op.create_index(op.f('ix_decisions_application_id'), 'decisions', ['application_id'], unique=False, schema='decision')
    op.create_table('paragraphs',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('doc_id', sa.UUID(), nullable=False),
    sa.Column('number', sa.Text(), nullable=True),
    sa.Column('page', sa.Integer(), nullable=True),
    sa.Column('text', sa.Text(), nullable=False),
    sa.Column('label', sa.Text(), nullable=True),
    sa.Column('confidence', sa.Numeric(precision=4, scale=3), nullable=True),
    sa.CheckConstraint("label IS NULL OR label IN ('requirement', 'definition', 'information')", name=op.f('ck_paragraphs_label')),
    sa.ForeignKeyConstraint(['doc_id'], ['rules.source_docs.id'], name=op.f('fk_paragraphs_doc_id_source_docs'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_paragraphs')),
    schema='rules'
    )
    op.create_index(op.f('ix_paragraphs_doc_id'), 'paragraphs', ['doc_id'], unique=False, schema='rules')
    op.create_table('rules',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('rule_set_id', sa.UUID(), nullable=False),
    sa.Column('code', sa.Text(), nullable=False),
    sa.Column('title', sa.Text(), nullable=False),
    sa.Column('body', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('applies_to', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
    sa.Column('effective_from', sa.Date(), nullable=False),
    sa.Column('effective_to', sa.Date(), nullable=True),
    sa.Column('status', sa.Text(), server_default=sa.text("'active'"), nullable=False),
    sa.Column('source_doc_id', sa.UUID(), nullable=False),
    sa.Column('source_para', sa.Text(), nullable=False),
    sa.Column('origin', sa.Text(), nullable=False),
    sa.Column('drafted_by', sa.UUID(), nullable=True),
    sa.Column('approved_by', sa.UUID(), nullable=True),
    sa.Column('supersedes_rule_id', sa.UUID(), nullable=True),
    sa.CheckConstraint("origin IN ('auto', 'manual')", name=op.f('ck_rules_origin')),
    sa.CheckConstraint("status IN ('active', 'superseded', 'repealed')", name=op.f('ck_rules_status')),
    sa.CheckConstraint('effective_to IS NULL OR effective_to >= effective_from', name=op.f('ck_rules_effective_range')),
    sa.ForeignKeyConstraint(['rule_set_id'], ['rules.rule_sets.id'], name=op.f('fk_rules_rule_set_id_rule_sets'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['source_doc_id'], ['rules.source_docs.id'], name=op.f('fk_rules_source_doc_id_source_docs')),
    sa.ForeignKeyConstraint(['supersedes_rule_id'], ['rules.rules.id'], name=op.f('fk_rules_supersedes_rule_id_rules')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_rules')),
    sa.UniqueConstraint('rule_set_id', 'code', name=op.f('uq_rules_rule_set_id_code')),
    schema='rules'
    )
    op.create_index(op.f('ix_rules_rule_set_id'), 'rules', ['rule_set_id'], unique=False, schema='rules')
    op.create_table('rule_results',
    sa.Column('decision_id', sa.UUID(), nullable=False),
    sa.Column('rule_id', sa.UUID(), nullable=False),
    sa.Column('result', sa.Text(), nullable=False),
    sa.Column('detail', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.CheckConstraint("result IN ('pass', 'fail', 'refer', 'not_applicable')", name=op.f('ck_rule_results_result')),
    sa.ForeignKeyConstraint(['decision_id'], ['decision.decisions.id'], name=op.f('fk_rule_results_decision_id_decisions'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['rule_id'], ['rules.rules.id'], name=op.f('fk_rule_results_rule_id_rules')),
    sa.PrimaryKeyConstraint('decision_id', 'rule_id', name=op.f('pk_rule_results')),
    schema='decision'
    )
    op.create_table('change_proposals',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('doc_id', sa.UUID(), nullable=False),
    sa.Column('paragraph_id', sa.UUID(), nullable=False),
    sa.Column('kind', sa.Text(), nullable=False),
    sa.Column('proposed', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('matched_words', sa.Text(), nullable=True),
    sa.Column('template', sa.Text(), nullable=True),
    sa.Column('confidence', sa.Numeric(precision=4, scale=3), nullable=True),
    sa.Column('status', sa.Text(), server_default=sa.text("'pending'"), nullable=False),
    sa.Column('drafted_by', sa.UUID(), nullable=True),
    sa.Column('reviewed_by', sa.UUID(), nullable=True),
    sa.CheckConstraint("kind IN ('new', 'amends', 'repeals')", name=op.f('ck_change_proposals_kind')),
    sa.CheckConstraint("status IN ('pending', 'approved', 'rejected')", name=op.f('ck_change_proposals_status')),
    sa.ForeignKeyConstraint(['doc_id'], ['rules.source_docs.id'], name=op.f('fk_change_proposals_doc_id_source_docs'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['paragraph_id'], ['rules.paragraphs.id'], name=op.f('fk_change_proposals_paragraph_id_paragraphs'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_change_proposals')),
    schema='rules'
    )
    op.create_index(op.f('ix_change_proposals_doc_id'), 'change_proposals', ['doc_id'], unique=False, schema='rules')


def downgrade() -> None:
    op.drop_index(op.f('ix_change_proposals_doc_id'), table_name='change_proposals', schema='rules')
    op.drop_table('change_proposals', schema='rules')
    op.drop_table('rule_results', schema='decision')
    op.drop_index(op.f('ix_rules_rule_set_id'), table_name='rules', schema='rules')
    op.drop_table('rules', schema='rules')
    op.drop_index(op.f('ix_paragraphs_doc_id'), table_name='paragraphs', schema='rules')
    op.drop_table('paragraphs', schema='rules')
    op.drop_index(op.f('ix_decisions_application_id'), table_name='decisions', schema='decision')
    op.drop_table('decisions', schema='decision')
    op.drop_table('source_docs', schema='rules')
    op.drop_table('rule_sets', schema='rules')
    op.drop_index('ix_applications_org_status_created', table_name='applications', schema='origination')
    op.drop_table('applications', schema='origination')

    for schema in reversed(SCHEMAS):
        op.execute(f"DROP SCHEMA IF EXISTS {schema} CASCADE")
