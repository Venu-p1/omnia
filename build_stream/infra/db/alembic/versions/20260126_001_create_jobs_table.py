"""Create jobs table

Revision ID: 20260126_001
Revises: 
Create Date: 2026-01-26 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260126_001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create jobs table with indexes."""
    op.create_table(
        'jobs',
        sa.Column('job_id', sa.String(length=36), nullable=False),
        sa.Column('client_id', sa.String(length=128), nullable=False),
        sa.Column('catalog_digest', sa.String(length=64), nullable=False),
        sa.Column('job_state', sa.String(length=20), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('tombstoned', sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint('job_id')
    )
    
    # Create indexes
    op.create_index('ix_jobs_client_id', 'jobs', ['client_id'])
    op.create_index('ix_jobs_job_state', 'jobs', ['job_state'])
    op.create_index('ix_jobs_created_at', 'jobs', ['created_at'])
    op.create_index('ix_jobs_tombstoned', 'jobs', ['tombstoned'])
    op.create_index('ix_jobs_client_state', 'jobs', ['client_id', 'job_state'])
    op.create_index('ix_jobs_created_tombstoned', 'jobs', ['created_at', 'tombstoned'])


def downgrade() -> None:
    """Drop jobs table."""
    op.drop_index('ix_jobs_created_tombstoned', table_name='jobs')
    op.drop_index('ix_jobs_client_state', table_name='jobs')
    op.drop_index('ix_jobs_tombstoned', table_name='jobs')
    op.drop_index('ix_jobs_created_at', table_name='jobs')
    op.drop_index('ix_jobs_job_state', table_name='jobs')
    op.drop_index('ix_jobs_client_id', table_name='jobs')
    op.drop_table('jobs')
