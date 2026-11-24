"""loans schema, rules.rules.stage and identity.users.active.

loans holds applications, engine evaluations (snapshots), decisions and each application's
step history (docs/contracts.md: loans owns these for December). stage says when a rule is
checked: origination, servicing or recovery. Calling hours (MF-05) are recovery; delayed payment
charges (MF-06) and charges outside the KFS (KF-02) are servicing. active is for the admin
Users page.

Revision ID: 0005
Revises: 0004
"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = '0005'
down_revision = '0004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS loans")
    op.create_table('applications',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('org_id', sa.UUID(), nullable=False),
    sa.Column('ref', sa.Text(), nullable=False),
    sa.Column('borrower_id', sa.UUID(), nullable=True),
    sa.Column('borrower_name', sa.Text(), nullable=False),
    sa.Column('purpose', sa.Text(), nullable=True),
    sa.Column('product', sa.Text(), nullable=False),
    sa.Column('amount_paise', sa.BigInteger(), nullable=False),
    sa.Column('tenor_months', sa.Integer(), nullable=False),
    sa.Column('rate_bps_month', sa.Integer(), nullable=False),
    sa.Column('fees', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
    sa.Column('prepayment_charge_paise', sa.BigInteger(), nullable=True),
    sa.Column('collateral', sa.Boolean(), nullable=True),
    sa.Column('household_income_annual_paise', sa.BigInteger(), nullable=True),
    sa.Column('existing_monthly_repayments_paise', sa.BigInteger(), nullable=True),
    sa.Column('status', sa.Text(), nullable=False),
    sa.Column('submitted_by', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('clock_timestamp()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('clock_timestamp()'), nullable=False),
    sa.CheckConstraint("status IN ('evaluated', 'recommended', 'approved', 'approved_modified', 'rejected')", name=op.f('ck_applications_status')),
    sa.CheckConstraint('amount_paise > 0', name=op.f('ck_applications_amount')),
    sa.CheckConstraint('rate_bps_month >= 0', name=op.f('ck_applications_rate')),
    sa.CheckConstraint('tenor_months > 0', name=op.f('ck_applications_tenor')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_applications')),
    sa.UniqueConstraint('ref', name=op.f('uq_applications_ref')),
    schema='loans'
    )
    op.create_index(op.f('ix_applications_borrower_id'), 'applications', ['borrower_id'], unique=False, schema='loans')
    op.create_index(op.f('ix_applications_org_id'), 'applications', ['org_id'], unique=False, schema='loans')
    op.create_index(op.f('ix_applications_status'), 'applications', ['status'], unique=False, schema='loans')
    op.create_table('evaluations',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('application_id', sa.UUID(), nullable=False),
    sa.Column('on_date', sa.Date(), nullable=False),
    sa.Column('amount_paise', sa.BigInteger(), nullable=False),
    sa.Column('outcome', sa.Text(), nullable=False),
    sa.Column('microfinance', sa.Boolean(), nullable=True),
    sa.Column('results', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('rules_used', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('offer', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('kfs', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('facts', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('run_by', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('clock_timestamp()'), nullable=False),
    sa.CheckConstraint("outcome IN ('pass', 'fail', 'refer')", name=op.f('ck_evaluations_outcome')),
    sa.ForeignKeyConstraint(['application_id'], ['loans.applications.id'], name=op.f('fk_evaluations_application_id_applications'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_evaluations')),
    schema='loans'
    )
    op.create_index(op.f('ix_evaluations_application_id'), 'evaluations', ['application_id'], unique=False, schema='loans')
    op.create_table('events',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('application_id', sa.UUID(), nullable=False),
    sa.Column('actor_id', sa.UUID(), nullable=False),
    sa.Column('action', sa.Text(), nullable=False),
    sa.Column('meta', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('clock_timestamp()'), nullable=False),
    sa.ForeignKeyConstraint(['application_id'], ['loans.applications.id'], name=op.f('fk_events_application_id_applications'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_events')),
    schema='loans'
    )
    op.create_index(op.f('ix_events_application_id'), 'events', ['application_id'], unique=False, schema='loans')
    op.create_table('decisions',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('application_id', sa.UUID(), nullable=False),
    sa.Column('recommendation', sa.Text(), nullable=False),
    sa.Column('recommended_paise', sa.BigInteger(), nullable=True),
    sa.Column('officer_id', sa.UUID(), nullable=False),
    sa.Column('officer_note', sa.Text(), nullable=True),
    sa.Column('recommended_at', sa.DateTime(timezone=True), server_default=sa.text('clock_timestamp()'), nullable=False),
    sa.Column('outcome', sa.Text(), nullable=True),
    sa.Column('approved_paise', sa.BigInteger(), nullable=True),
    sa.Column('checker_id', sa.UUID(), nullable=True),
    sa.Column('checker_note', sa.Text(), nullable=True),
    sa.Column('decided_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('evaluation_id', sa.UUID(), nullable=True),
    sa.Column('ledger_seq', sa.BigInteger(), nullable=True),
    sa.CheckConstraint("outcome IS NULL OR outcome IN ('approved', 'approved_modified', 'rejected')", name=op.f('ck_decisions_outcome')),
    sa.CheckConstraint("recommendation IN ('approve', 'approve_modified', 'reject')", name=op.f('ck_decisions_recommendation')),
    sa.CheckConstraint('checker_id IS NULL OR checker_id <> officer_id', name=op.f('ck_decisions_four_eyes')),
    sa.ForeignKeyConstraint(['application_id'], ['loans.applications.id'], name=op.f('fk_decisions_application_id_applications'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['evaluation_id'], ['loans.evaluations.id'], name=op.f('fk_decisions_evaluation_id_evaluations')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_decisions')),
    sa.UniqueConstraint('application_id', name=op.f('uq_decisions_application_id')),
    schema='loans'
    )
    op.add_column('users', sa.Column('active', sa.Boolean(), server_default=sa.text('true'), nullable=False), schema='identity')
    op.add_column('rules', sa.Column('stage', sa.Text(), server_default=sa.text("'origination'"), nullable=False), schema='rules')
    op.create_check_constraint(
        op.f("ck_rules_stage"), "rules", "stage IN ('origination', 'servicing', 'recovery')",
        schema="rules",
    )
    op.execute("UPDATE rules.rules SET stage = 'recovery' WHERE code = 'MF-05'")
    op.execute("UPDATE rules.rules SET stage = 'servicing' WHERE code IN ('MF-06', 'KF-02')")


def downgrade() -> None:
    op.drop_constraint(op.f("ck_rules_stage"), "rules", schema="rules")
    op.drop_column('rules', 'stage', schema='rules')
    op.drop_column('users', 'active', schema='identity')
    op.drop_table('decisions', schema='loans')
    op.drop_index(op.f('ix_events_application_id'), table_name='events', schema='loans')
    op.drop_table('events', schema='loans')
    op.drop_index(op.f('ix_evaluations_application_id'), table_name='evaluations', schema='loans')
    op.drop_table('evaluations', schema='loans')
    op.drop_index(op.f('ix_applications_status'), table_name='applications', schema='loans')
    op.drop_index(op.f('ix_applications_org_id'), table_name='applications', schema='loans')
    op.drop_index(op.f('ix_applications_borrower_id'), table_name='applications', schema='loans')
    op.drop_table('applications', schema='loans')
    op.execute("DROP SCHEMA IF EXISTS loans CASCADE")
