"""set null on delete for videos user_id foreign key

Revision ID: e3f81b2a9c4d
Revises: b5e8c1d3f2a4
Create Date: 2026-11-07 08:45:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e3f81b2a9c4d"
down_revision: Union[str, None] = "b5e8c1d3f2a4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Ensure deleting a user sets videos.user_id to NULL instead of cascading.
    This preserves canonical shared videos referenced by other users via user_videos.
    """
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.drop_constraint("videos_user_id_fkey", "videos", type_="foreignkey")
        op.create_foreign_key(
            "fk_videos_user_id",
            "videos",
            "users",
            ["user_id"],
            ["id"],
            ondelete="SET NULL",
        )
    else:
        # SQLite / batch mode fallback
        with op.batch_alter_table("videos") as batch_op:
            batch_op.create_foreign_key(
                "fk_videos_user_id",
                "users",
                ["user_id"],
                ["id"],
                ondelete="SET NULL",
            )


def downgrade() -> None:
    """
    Restore previous CASCADE foreign key constraint on videos.user_id.
    """
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.drop_constraint("fk_videos_user_id", "videos", type_="foreignkey")
        op.create_foreign_key(
            "videos_user_id_fkey",
            "videos",
            "users",
            ["user_id"],
            ["id"],
            ondelete="CASCADE",
        )
    else:
        # SQLite / batch mode fallback
        with op.batch_alter_table("videos") as batch_op:
            batch_op.create_foreign_key(
                "videos_user_id_fkey",
                "users",
                ["user_id"],
                ["id"],
                ondelete="CASCADE",
            )
