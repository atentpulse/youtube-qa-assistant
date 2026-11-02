"""add user_videos and conversation video_id

Revision ID: d4f81a792e31
Revises: 0c2a55196561
Create Date: 2026-11-01 23:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4f81a792e31'
down_revision: Union[str, Sequence[str], None] = '0c2a55196561'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create user_videos association table
    op.create_table(
        'user_videos',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('video_id', sa.String(length=20), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['video_id'], ['videos.video_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'video_id', name='uq_user_videos_user_video')
    )
    op.create_index(op.f('ix_user_videos_id'), 'user_videos', ['id'], unique=False)
    op.create_index(op.f('ix_user_videos_user_id'), 'user_videos', ['user_id'], unique=False)
    op.create_index(op.f('ix_user_videos_video_id'), 'user_videos', ['video_id'], unique=False)

    # 2. Backfill existing video ownership into user_videos
    # Safe across SQLite and PostgreSQL
    connection = op.get_bind()
    connection.execute(sa.text("""
        INSERT INTO user_videos (user_id, video_id, created_at)
        SELECT user_id, video_id, created_at FROM videos WHERE user_id IS NOT NULL
    """))

    # 3. Add video_id to conversations table
    with op.batch_alter_table('conversations') as batch_op:
        batch_op.add_column(
            sa.Column('video_id', sa.String(length=20), nullable=True)
        )
        batch_op.create_foreign_key(
            'fk_conversations_video_id',
            'videos',
            ['video_id'],
            ['video_id'],
            ondelete='SET NULL'
        )
    op.create_index(op.f('ix_conversations_video_id'), 'conversations', ['video_id'], unique=False)

    # 4. Make videos.user_id nullable to allow purely canonical video records
    with op.batch_alter_table('videos') as batch_op:
        batch_op.alter_column('user_id', existing_type=sa.Integer(), nullable=True)


def downgrade() -> None:
    connection = op.get_bind()

    # 1. Backfill videos.user_id from user_videos for any video where user_id IS NULL
    # Safe across SQLite and PostgreSQL
    connection.execute(sa.text("""
        UPDATE videos
        SET user_id = (
            SELECT user_id FROM user_videos
            WHERE user_videos.video_id = videos.video_id
            ORDER BY created_at ASC
            LIMIT 1
        )
        WHERE user_id IS NULL AND EXISTS (
            SELECT 1 FROM user_videos WHERE user_videos.video_id = videos.video_id
        )
    """))

    # 2. For any orphan video that has no user association in user_videos:
    # Under legacy schema (0c2a55196561), videos.user_id was NOT NULL.
    # To satisfy this constraint safely on rollback, remove orphan videos without an owner.
    connection.execute(sa.text("""
        DELETE FROM videos WHERE user_id IS NULL
    """))

    # 3. Reverse 4: make videos.user_id not null (safe now that all nulls are resolved)
    with op.batch_alter_table('videos') as batch_op:
        batch_op.alter_column('user_id', existing_type=sa.Integer(), nullable=False)

    # 4. Reverse 3: drop conversations.video_id
    with op.batch_alter_table('conversations') as batch_op:
        batch_op.drop_constraint('fk_conversations_video_id', type_='foreignkey')
        batch_op.drop_index(op.f('ix_conversations_video_id'))
        batch_op.drop_column('video_id')

    # 5. Reverse 1: drop user_videos table
    op.drop_index(op.f('ix_user_videos_video_id'), table_name='user_videos')
    op.drop_index(op.f('ix_user_videos_user_id'), table_name='user_videos')
    op.drop_index(op.f('ix_user_videos_id'), table_name='user_videos')
    op.drop_table('user_videos')
