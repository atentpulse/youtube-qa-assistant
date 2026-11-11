"""add email_otps table

Revision ID: a1b2c3d4e5f6
Revises: f4a92b3c1d5e
Create Date: 2026-11-11 11:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'f4a92b3c1d5e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'email_otps',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('otp_hash', sa.String(length=255), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('attempts', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('max_attempts', sa.Integer(), nullable=False, server_default='5'),
        sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_email_otps_id'), 'email_otps', ['id'], unique=False)
    op.create_index(op.f('ix_email_otps_email'), 'email_otps', ['email'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_email_otps_email'), table_name='email_otps')
    op.drop_index(op.f('ix_email_otps_id'), table_name='email_otps')
    op.drop_table('email_otps')
