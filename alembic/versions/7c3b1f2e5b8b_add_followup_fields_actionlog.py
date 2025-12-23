"""add followup fields to action_logs

Revision ID: 7c3b1f2e5b8b
Revises: 21d3b906189e
Create Date: 2025-12-15 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '7c3b1f2e5b8b'
down_revision = '21d3b906189e'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_cols = {col['name'] for col in inspector.get_columns('action_logs')}

    if 'is_followup_pending' not in existing_cols:
        op.add_column('action_logs', sa.Column('is_followup_pending', sa.Boolean(), nullable=False, server_default=sa.false()))
    if 'expected_reply_date' not in existing_cols:
        op.add_column('action_logs', sa.Column('expected_reply_date', sa.Date(), nullable=True))
    if 'followup_sent' not in existing_cols:
        op.add_column('action_logs', sa.Column('followup_sent', sa.Boolean(), nullable=False, server_default=sa.false()))

    # Add indexes to speed up daily follow-up query (only if columns exist)
    existing_indexes = {idx['name'] for idx in inspector.get_indexes('action_logs')}
    if 'ix_action_logs_is_followup_pending' not in existing_indexes and 'is_followup_pending' in existing_cols:
        op.create_index('ix_action_logs_is_followup_pending', 'action_logs', ['is_followup_pending'])
    if 'ix_action_logs_expected_reply_date' not in existing_indexes and 'expected_reply_date' in existing_cols:
        op.create_index('ix_action_logs_expected_reply_date', 'action_logs', ['expected_reply_date'])
    if 'ix_action_logs_followup_sent' not in existing_indexes and 'followup_sent' in existing_cols:
        op.create_index('ix_action_logs_followup_sent', 'action_logs', ['followup_sent'])

    # NOTE: Do not alter server defaults on SQLite (causes syntax errors)
    # If needed for other DBs, handle separately, but skip for SQLite


def downgrade() -> None:
    op.drop_index('ix_action_logs_followup_sent', table_name='action_logs')
    op.drop_index('ix_action_logs_expected_reply_date', table_name='action_logs')
    op.drop_index('ix_action_logs_is_followup_pending', table_name='action_logs')
    op.drop_column('action_logs', 'followup_sent')
    op.drop_column('action_logs', 'expected_reply_date')
    op.drop_column('action_logs', 'is_followup_pending')


