"""add bug_reports table

Revision ID: b5e8c1d3f2a4
Revises: d4f81a792e31
Create Date: 2026-11-06 13:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b5e8c1d3f2a4'
down_revision: Union[str, Sequence[str], None] = 'd4f81a792e31'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'bug_reports',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=False, server_default='general'),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='open'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_bug_reports_id'), 'bug_reports', ['id'], unique=False)
    op.create_index(op.f('ix_bug_reports_user_id'), 'bug_reports', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_bug_reports_user_id'), table_name='bug_reports')
    op.drop_index(op.f('ix_bug_reports_id'), table_name='bug_reports')
    op.drop_table('bug_reports')
