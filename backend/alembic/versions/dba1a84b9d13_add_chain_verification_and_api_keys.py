"""add chain verification fields and api keys

Revision ID: dba1a84b9d13
Revises: ac12810d0147
Create Date: 2026-07-26 00:30:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'dba1a84b9d13'
down_revision: Union[str, None] = 'ac12810d0147'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('dispute_evidence', sa.Column('chain', sa.String(length=50), nullable=True))
    op.add_column('dispute_evidence', sa.Column('verification_status', sa.String(length=30), nullable=True))
    op.add_column('dispute_evidence', sa.Column('verification_details', sa.JSON(), nullable=True))

    op.add_column('disputes', sa.Column('callback_url', sa.String(length=2000), nullable=True))

    op.create_table(
        'api_keys',
        sa.Column('created_by_user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('wallet_id', sa.String(length=255), nullable=False),
        sa.Column('key_hash', sa.String(length=64), nullable=False),
        sa.Column('key_prefix', sa.String(length=12), nullable=False),
        sa.Column('label', sa.String(length=255), nullable=True),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_api_keys_created_by_user_id'), 'api_keys', ['created_by_user_id'], unique=False)
    op.create_index(op.f('ix_api_keys_wallet_id'), 'api_keys', ['wallet_id'], unique=False)
    op.create_index(op.f('ix_api_keys_key_hash'), 'api_keys', ['key_hash'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_api_keys_key_hash'), table_name='api_keys')
    op.drop_index(op.f('ix_api_keys_wallet_id'), table_name='api_keys')
    op.drop_index(op.f('ix_api_keys_created_by_user_id'), table_name='api_keys')
    op.drop_table('api_keys')

    op.drop_column('disputes', 'callback_url')

    op.drop_column('dispute_evidence', 'verification_details')
    op.drop_column('dispute_evidence', 'verification_status')
    op.drop_column('dispute_evidence', 'chain')
