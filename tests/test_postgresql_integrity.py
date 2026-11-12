import pytest
from sqlalchemy import text
from app.database.database import engine as pg_engine
from app.services.lock_service import VideoIngestionLock


@pytest.fixture(autouse=True)
def require_postgresql_environment(require_postgres):
    """Ensure PostgreSQL is accessible before running any test in this module."""
    pass


def test_postgresql_foreign_key_cascades_and_set_null():
    """
    Directly query PostgreSQL information_schema to verify constraint enforcement:
    - fk_videos_user_id: SET NULL
    - conversations_user_id_fkey: CASCADE
    - messages_conversation_id_fkey: CASCADE
    - oauth_exchange_codes_user_id_fkey: CASCADE
    """
    if pg_engine.dialect.name != "postgresql":
        pytest.skip("Test requires real PostgreSQL engine")

    with pg_engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT tc.table_name, tc.constraint_name, rc.delete_rule
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.referential_constraints AS rc
              ON tc.constraint_name = rc.constraint_name
              AND tc.table_schema = rc.constraint_schema
            WHERE tc.table_name IN ('videos', 'conversations', 'messages', 'oauth_exchange_codes', 'question_cache')
              AND tc.constraint_type = 'FOREIGN KEY';
        """)).fetchall()

        rule_map = {row[1]: row[2] for row in rows}

        # Check videos.user_id -> SET NULL (Phase 1A shared video protection)
        assert rule_map.get("fk_videos_user_id") == "SET NULL", (
            f"Expected fk_videos_user_id to be 'SET NULL', found {rule_map.get('fk_videos_user_id')}"
        )
        # Check conversations.user_id -> CASCADE
        assert rule_map.get("conversations_user_id_fkey") == "CASCADE", (
            f"Expected conversations_user_id_fkey to be 'CASCADE', found {rule_map.get('conversations_user_id_fkey')}"
        )
        # Check messages.conversation_id -> CASCADE
        assert rule_map.get("messages_conversation_id_fkey") == "CASCADE", (
            f"Expected messages_conversation_id_fkey to be 'CASCADE', found {rule_map.get('messages_conversation_id_fkey')}"
        )
        # Check oauth_exchange_codes.user_id -> CASCADE
        assert rule_map.get("oauth_exchange_codes_user_id_fkey") == "CASCADE", (
            f"Expected oauth_exchange_codes_user_id_fkey to be 'CASCADE', found {rule_map.get('oauth_exchange_codes_user_id_fkey')}"
        )


def test_postgresql_question_cache_unique_index():
    """Verify on PostgreSQL that question_cache has a UNIQUE constraint/index on cache_key."""
    if pg_engine.dialect.name != "postgresql":
        pytest.skip("Test requires real PostgreSQL engine")

    with pg_engine.connect() as conn:
        index_row = conn.execute(text("""
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE tablename = 'question_cache' AND indexname = 'uq_question_cache_cache_key';
        """)).first()

        assert index_row is not None, "Unique index uq_question_cache_cache_key must exist on question_cache"
        assert "UNIQUE INDEX" in index_row[1], f"Expected index to be UNIQUE, got: {index_row[1]}"


def test_postgresql_advisory_lock_cross_session_detection():
    """
    Verify PostgreSQL advisory locking across two independent database sessions:
    - Session 1 acquires lock on video_id
    - Session 2 detects is_locked == True
    - Session 1 releases lock
    - Session 2 detects is_locked == False
    """
    if pg_engine.dialect.name != "postgresql":
        pytest.skip("Test requires real PostgreSQL engine")

    from sqlalchemy.orm import sessionmaker
    SessionMaker = sessionmaker(bind=pg_engine)

    session1 = SessionMaker()
    session2 = SessionMaker()
    test_video_id = "pg_cross_session_advisory_vid"

    try:
        lock1 = VideoIngestionLock(session1, test_video_id)
        acquired = lock1.acquire()
        assert acquired is True, "Session 1 should acquire advisory lock"

        # Session 2 checks lock
        is_locked_from_s2 = VideoIngestionLock.is_locked(session2, test_video_id)
        assert is_locked_from_s2 is True, "Session 2 must detect active lock held by Session 1"

        # Release lock in Session 1
        released = lock1.release()
        assert released is True

        # Session 2 checks lock again
        is_locked_after_release = VideoIngestionLock.is_locked(session2, test_video_id)
        assert is_locked_after_release is False, "Session 2 must detect lock is released"
    finally:
        session1.close()
        session2.close()
