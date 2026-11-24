"""loans.events.seq and loans.evaluations.seq: insert order.

The step history and "latest evaluation" are read in insert order, because timestamps can tie
(seeded steps share a time). Existing rows are numbered in their stored order.

Revision ID: 0006
Revises: 0005
"""
import sqlalchemy as sa

from alembic import op

revision = '0006'
down_revision = '0005'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('evaluations', sa.Column('seq', sa.BigInteger(), sa.Identity(always=False), nullable=False), schema='loans')
    op.create_unique_constraint(op.f('uq_evaluations_seq'), 'evaluations', ['seq'], schema='loans')
    op.add_column('events', sa.Column('seq', sa.BigInteger(), sa.Identity(always=False), nullable=False), schema='loans')
    op.create_unique_constraint(op.f('uq_events_seq'), 'events', ['seq'], schema='loans')


def downgrade() -> None:
    op.drop_constraint(op.f('uq_events_seq'), 'events', schema='loans', type_='unique')
    op.drop_column('events', 'seq', schema='loans')
    op.drop_constraint(op.f('uq_evaluations_seq'), 'evaluations', schema='loans', type_='unique')
    op.drop_column('evaluations', 'seq', schema='loans')
