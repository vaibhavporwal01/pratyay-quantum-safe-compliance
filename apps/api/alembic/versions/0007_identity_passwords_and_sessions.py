"""identity: password sign-in and server-side sessions.

users gains password_hash (Argon2id), failed_attempts and locked_until. sessions stores only
the SHA-256 of each cookie token, with idle (last_seen_at) and absolute (expires_at) limits.

Revision ID: 0007
Revises: 0006
"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = '0007'
down_revision = '0006'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column('password_hash', sa.Text(), nullable=True), schema='identity')
    op.add_column('users', sa.Column('failed_attempts', sa.Integer(), server_default=sa.text('0'), nullable=False), schema='identity')
    op.add_column('users', sa.Column('locked_until', sa.DateTime(timezone=True), nullable=True), schema='identity')
    op.create_table(
        'sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('token_sha256', sa.LargeBinary(), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['identity.users.id'], name=op.f('fk_sessions_user_id_users'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_sessions')),
        sa.UniqueConstraint('token_sha256', name=op.f('uq_sessions_token_sha256')),
        schema='identity',
    )
    op.create_index(op.f('ix_identity_sessions_user_id'), 'sessions', ['user_id'], unique=False, schema='identity')


def downgrade() -> None:
    op.drop_index(op.f('ix_identity_sessions_user_id'), table_name='sessions', schema='identity')
    op.drop_table('sessions', schema='identity')
    op.drop_column('users', 'locked_until', schema='identity')
    op.drop_column('users', 'failed_attempts', schema='identity')
    op.drop_column('users', 'password_hash', schema='identity')
