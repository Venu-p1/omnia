"""Create job_stages table

Revision ID: 20260126_002
Revises: 20260126_001
Create Date: 2026-01-26 16:01:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260126_002'
down_revision: Union[str, None] = '20260126_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create job_stages table with foreign key and indexes."""
    op.create_table(
        'job_stages',
        sa.Column('job_id', sa.String(length=36), nullable=False),
        sa.Column('stage_name', sa.String(length=30), nullable=False),
        sa.Column('stage_state', sa.String(length=20), nullable=False),
        sa.Column('attempt', sa.Integer(), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_code', sa.String(length=50), nullable=True),
        sa.Column('error_summary', sa.Text(), nullable=True),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['job_id'], ['jobs.job_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('job_id', 'stage_name')
    )
    
    # Create indexes
    op.create_index('ix_stages_stage_state', 'job_stages', ['stage_state'])
    op.create_index('ix_stages_job_state', 'job_stages', ['job_id', 'stage_state'])


def downgrade() -> None:
    """Drop job_stages table."""
    op.drop_index('ix_stages_job_state', table_name='job_stages')
    op.drop_index('ix_stages_stage_state', table_name='job_stages')
    op.drop_table('job_stages')
