"""database integrity and schema refinements

Revision ID: f4a92b3c1d5e
Revises: e3f81b2a9c4d
Create Date: 2026-11-07 10:00:00.000000

"""

import hashlib
import json
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column


# revision identifiers, used by Alembic.
revision: str = "f4a92b3c1d5e"
down_revision: Union[str, None] = "e3f81b2a9c4d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _compute_key(video_id: str, question: str) -> str:
    norm_q = " ".join(str(question).strip().lower().split())
    payload = json.dumps(
        {
            "ex": False,
            "len": "balanced",
            "model": "default",
            "q": norm_q,
            "struct": True,
            "style": "explanatory",
            "v": "v1",
            "video_id": str(video_id).strip(),
        },
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def upgrade() -> None:
    bind = op.get_bind()
    dialect_name = bind.dialect.name if bind is not None else "postgresql"
    inspector = sa.inspect(bind)
    table_names = inspector.get_table_names()

    # 1. Users: add role and token_version
    if "users" in table_names:
        user_cols = [c["name"] for c in inspector.get_columns("users")]
        if "role" not in user_cols:
            op.add_column(
                "users",
                sa.Column(
                    "role",
                    sa.String(length=20),
                    server_default="user",
                    nullable=False,
                ),
            )
        if "token_version" not in user_cols:
            op.add_column(
                "users",
                sa.Column(
                    "token_version",
                    sa.Integer(),
                    server_default="1",
                    nullable=False,
                ),
            )

    # 2. Videos: add error_message and processing_started_at
    if "videos" in table_names:
        vid_cols = [c["name"] for c in inspector.get_columns("videos")]
        if "error_message" not in vid_cols:
            op.add_column(
                "videos",
                sa.Column("error_message", sa.String(length=1000), nullable=True),
            )
        if "processing_started_at" not in vid_cols:
            op.add_column(
                "videos",
                sa.Column("processing_started_at", sa.DateTime(timezone=True), nullable=True),
            )

    # 3. Conversations: enforce ON DELETE CASCADE for user_id
    if "conversations" in table_names:
        if dialect_name == "postgresql":
            op.drop_constraint("conversations_user_id_fkey", "conversations", type_="foreignkey")
            op.create_foreign_key(
                "conversations_user_id_fkey",
                "conversations",
                "users",
                ["user_id"],
                ["id"],
                ondelete="CASCADE",
            )
        else:
            with op.batch_alter_table("conversations") as batch_op:
                batch_op.create_foreign_key(
                    "conversations_user_id_fkey",
                    "users",
                    ["user_id"],
                    ["id"],
                    ondelete="CASCADE",
                )

    # 4. Messages: enforce ON DELETE CASCADE for conversation_id and add citations
    if "messages" in table_names:
        msg_cols = [c["name"] for c in inspector.get_columns("messages")]
        if "citations" not in msg_cols:
            op.add_column(
                "messages",
                sa.Column("citations", sa.Text(), nullable=True),
            )
        if dialect_name == "postgresql":
            op.drop_constraint("messages_conversation_id_fkey", "messages", type_="foreignkey")
            op.create_foreign_key(
                "messages_conversation_id_fkey",
                "messages",
                "conversations",
                ["conversation_id"],
                ["id"],
                ondelete="CASCADE",
            )
        else:
            with op.batch_alter_table("messages") as batch_op:
                batch_op.create_foreign_key(
                    "messages_conversation_id_fkey",
                    "conversations",
                    ["conversation_id"],
                    ["id"],
                    ondelete="CASCADE",
                )

    # 5. OAuth exchange codes table
    if "oauth_exchange_codes" not in table_names:
        op.create_table(
            "oauth_exchange_codes",
            sa.Column("code_hash", sa.String(length=64), primary_key=True),
            sa.Column(
                "user_id",
                sa.Integer(),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("used", sa.Boolean(), server_default=sa.false(), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
        )
        op.create_index(
            "ix_oauth_exchange_codes_user_id",
            "oauth_exchange_codes",
            ["user_id"],
        )

    # 6. Question Cache: add cache_key, backfill, make not null, replace unique constraint
    if "question_cache" in table_names:
        qc_cols = [c["name"] for c in inspector.get_columns("question_cache")]
        if "cache_key" not in qc_cols:
            op.add_column(
                "question_cache",
                sa.Column("cache_key", sa.String(length=64), nullable=True),
            )

        qc_table = table(
            "question_cache",
            column("id", sa.Integer),
            column("video_id", sa.String),
            column("question", sa.Text),
            column("cache_key", sa.String),
        )
        conn = op.get_bind()
        rows = conn.execute(sa.select(qc_table.c.id, qc_table.c.video_id, qc_table.c.question)).fetchall()
        for row in rows:
            r_id, v_id, q_text = row[0], row[1], row[2]
            c_key = _compute_key(v_id, q_text)
            conn.execute(
                qc_table.update()
                .where(qc_table.c.id == r_id)
                .values(cache_key=c_key)
            )

        if dialect_name == "postgresql":
            op.alter_column("question_cache", "cache_key", nullable=False)
            op.drop_constraint("uq_question_cache_video_question", "question_cache", type_="unique")
            op.create_unique_constraint(
                "uq_question_cache_cache_key",
                "question_cache",
                ["cache_key"],
            )
            op.create_index(
                "ix_question_cache_cache_key",
                "question_cache",
                ["cache_key"],
            )
        else:
            with op.batch_alter_table("question_cache") as batch_op:
                batch_op.alter_column("cache_key", nullable=False)
                batch_op.drop_constraint("uq_question_cache_video_question", type_="unique")
                batch_op.create_unique_constraint("uq_question_cache_cache_key", ["cache_key"])
                batch_op.create_index("ix_question_cache_cache_key", ["cache_key"])


def downgrade() -> None:
    bind = op.get_bind()
    dialect_name = bind.dialect.name if bind is not None else "postgresql"

    # 1. Question Cache
    if dialect_name == "postgresql":
        op.drop_index("ix_question_cache_cache_key", table_name="question_cache")
        op.drop_constraint("uq_question_cache_cache_key", "question_cache", type_="unique")
        op.create_unique_constraint(
            "uq_question_cache_video_question",
            "question_cache",
            ["video_id", "question"],
        )
        op.drop_column("question_cache", "cache_key")
    else:
        with op.batch_alter_table("question_cache") as batch_op:
            batch_op.drop_index("ix_question_cache_cache_key")
            batch_op.drop_constraint("uq_question_cache_cache_key", type_="unique")
            batch_op.create_unique_constraint("uq_question_cache_video_question", ["video_id", "question"])
            batch_op.drop_column("cache_key")

    # 2. OAuth exchange codes
    op.drop_index("ix_oauth_exchange_codes_user_id", table_name="oauth_exchange_codes")
    op.drop_table("oauth_exchange_codes")

    # 3. Messages
    if dialect_name == "postgresql":
        op.drop_constraint("messages_conversation_id_fkey", "messages", type_="foreignkey")
        op.create_foreign_key(
            "messages_conversation_id_fkey",
            "messages",
            "conversations",
            ["conversation_id"],
            ["id"],
        )
    else:
        with op.batch_alter_table("messages") as batch_op:
            batch_op.create_foreign_key(
                "messages_conversation_id_fkey",
                "conversations",
                ["conversation_id"],
                ["id"],
            )
    op.drop_column("messages", "citations")

    # 4. Conversations
    if dialect_name == "postgresql":
        op.drop_constraint("conversations_user_id_fkey", "conversations", type_="foreignkey")
        op.create_foreign_key(
            "conversations_user_id_fkey",
            "conversations",
            "users",
            ["user_id"],
            ["id"],
        )
    else:
        with op.batch_alter_table("conversations") as batch_op:
            batch_op.create_foreign_key(
                "conversations_user_id_fkey",
                "users",
                ["user_id"],
                ["id"],
            )

    # 5. Videos
    op.drop_column("videos", "processing_started_at")
    op.drop_column("videos", "error_message")

    # 6. Users
    op.drop_column("users", "token_version")
    op.drop_column("users", "role")
