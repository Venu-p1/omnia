"""Create idempotency_keys table

Revision ID: 20260126_003
Revises: 20260126_002
Create Date: 2026-01-26 16:02:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260126_003'
down_revision: Union[str, None] = '20260126_002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create idempotency_keys table with indexes."""
    op.create_table(
        'idempotency_keys',
        sa.Column('idempotency_key', sa.String(length=255), nullable=False),
        sa.Column('job_id', sa.String(length=36), nullable=False),
        sa.Column('request_fingerprint', sa.String(length=64), nullable=False),
        sa.Column('client_id', sa.String(length=128), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('idempotency_key')
    )
    
    # Create indexes
    op.create_index('ix_idempotency_keys_job_id', 'idempotency_keys', ['job_id'])
    op.create_index('ix_idempotency_keys_client_id', 'idempotency_keys', ['client_id'])
    op.create_index('ix_idempotency_keys_created_at', 'idempotency_keys', ['created_at'])
    op.create_index('ix_idempotency_keys_expires_at', 'idempotency_keys', ['expires_at'])
    op.create_index('ix_idempotency_client_created', 'idempotency_keys', ['client_id', 'created_at'])
    op.create_index('ix_idempotency_expires', 'idempotency_keys', ['expires_at'])


def downgrade() -> None:
    """Drop idempotency_keys table."""
    op.drop_index('ix_idempotency_expires', table_name='idempotency_keys')
    op.drop_index('ix_idempotency_client_created', table_name='idempotency_keys')
    op.drop_index('ix_idempotency_keys_expires_at', table_name='idempotency_keys')
    op.drop_index('ix_idempotency_keys_created_at', table_name='idempotency_keys')
    op.drop_index('ix_idempotency_keys_client_id', table_name='idempotency_keys')
    op.drop_index('ix_idempotency_keys_job_id', table_name='idempotency_keys')
    op.drop_table('idempotency_keys')
