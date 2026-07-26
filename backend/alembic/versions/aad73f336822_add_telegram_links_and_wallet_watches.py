"""add telegram links and wallet watches

Revision ID: aad73f336822
Revises: dba1a84b9d13
Create Date: 2026-07-26 12:15:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'aad73f336822'
down_revision: Union[str, None] = 'dba1a84b9d13'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'telegram_links',
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('telegram_chat_id', sa.String(length=64), nullable=False),
        sa.Column('telegram_username', sa.String(length=255), nullable=True),
        sa.Column('linked_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_telegram_links_telegram_chat_id'), 'telegram_links', ['telegram_chat_id'], unique=True)
    op.create_unique_constraint('uq_telegram_links_user_id', 'telegram_links', ['user_id'])

    op.create_table(
        'wallet_watches',
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('wallet_id', sa.String(length=255), nullable=False),
        sa.Column('label', sa.String(length=255), nullable=True),
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'wallet_id', name='uq_wallet_watch_user_wallet'),
    )
    op.create_index(op.f('ix_wallet_watches_user_id'), 'wallet_watches', ['user_id'], unique=False)
    op.create_index(op.f('ix_wallet_watches_wallet_id'), 'wallet_watches', ['wallet_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_wallet_watches_wallet_id'), table_name='wallet_watches')
    op.drop_index(op.f('ix_wallet_watches_user_id'), table_name='wallet_watches')
    op.drop_table('wallet_watches')

    op.drop_constraint('uq_telegram_links_user_id', 'telegram_links', type_='unique')
    op.drop_index(op.f('ix_telegram_links_telegram_chat_id'), table_name='telegram_links')
    op.drop_table('telegram_links')
