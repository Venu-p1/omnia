"""Create audit_events table

Revision ID: 20260126_004
Revises: 20260126_003
Create Date: 2026-01-26 16:03:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260126_004'
down_revision: Union[str, None] = '20260126_003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create audit_events table with indexes."""
    op.create_table(
        'audit_events',
        sa.Column('event_id', sa.String(length=36), nullable=False),
        sa.Column('job_id', sa.String(length=36), nullable=False),
        sa.Column('event_type', sa.String(length=50), nullable=False),
        sa.Column('correlation_id', sa.String(length=36), nullable=False),
        sa.Column('client_id', sa.String(length=128), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('details', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('event_id')
    )
    
    # Create indexes
    op.create_index('ix_audit_events_job_id', 'audit_events', ['job_id'])
    op.create_index('ix_audit_events_event_type', 'audit_events', ['event_type'])
    op.create_index('ix_audit_events_correlation_id', 'audit_events', ['correlation_id'])
    op.create_index('ix_audit_events_client_id', 'audit_events', ['client_id'])
    op.create_index('ix_audit_events_timestamp', 'audit_events', ['timestamp'])
    op.create_index('ix_audit_job_timestamp', 'audit_events', ['job_id', 'timestamp'])
    op.create_index('ix_audit_correlation', 'audit_events', ['correlation_id'])
    op.create_index('ix_audit_client_timestamp', 'audit_events', ['client_id', 'timestamp'])


def downgrade() -> None:
    """Drop audit_events table."""
    op.drop_index('ix_audit_client_timestamp', table_name='audit_events')
    op.drop_index('ix_audit_correlation', table_name='audit_events')
    op.drop_index('ix_audit_job_timestamp', table_name='audit_events')
    op.drop_index('ix_audit_events_timestamp', table_name='audit_events')
    op.drop_index('ix_audit_events_client_id', table_name='audit_events')
    op.drop_index('ix_audit_events_correlation_id', table_name='audit_events')
    op.drop_index('ix_audit_events_event_type', table_name='audit_events')
    op.drop_index('ix_audit_events_job_id', table_name='audit_events')
    op.drop_table('audit_events')
