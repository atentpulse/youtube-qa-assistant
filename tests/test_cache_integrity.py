import concurrent.futures
import pytest
from app.models.question_cache import QuestionCache
from app.models.video import Video
from app.services.cache_service import CacheService
from app.services.video_storage_service import VideoStorageService


def test_cache_key_determinism():
    """Verify that identical inputs produce the exact same SHA-256 cache key regardless of whitespace or casing."""
    k1 = CacheService.compute_cache_key(
        video_id="vid_test_123",
        question="  What is the  main topic? ",
        answer_length="balanced",
        response_style="explanatory",
    )
    k2 = CacheService.compute_cache_key(
        video_id="vid_test_123",
        question="what is the main topic?",
        answer_length="balanced",
        response_style="explanatory",
    )
    assert k1 == k2
    assert len(k1) == 64


def test_cache_key_preference_isolation():
    """Verify that different answer lengths or response styles produce distinct cache keys."""
    concise_key = CacheService.compute_cache_key(
        video_id="vid_test_123",
        question="What is this video about?",
        answer_length="concise",
        response_style="explanatory",
    )
    detailed_key = CacheService.compute_cache_key(
        video_id="vid_test_123",
        question="What is this video about?",
        answer_length="detailed",
        response_style="explanatory",
    )
    technical_key = CacheService.compute_cache_key(
        video_id="vid_test_123",
        question="What is this video about?",
        answer_length="balanced",
        response_style="technical",
    )
    assert concise_key != detailed_key
    assert concise_key != technical_key
    assert detailed_key != technical_key


def test_long_question_cache_no_btree_error(db, test_user):
    """
    Verify that an extremely long question (> 3,000 characters) is successfully
    cached, updated, and retrieved without btree index size errors.
    """
    storage = VideoStorageService(db)
    storage.create_or_update_video("long_q_vid", test_user.id, "processed", "Long Q Video")

    cache = CacheService(db)
    long_question = "Why is this system effective? " * 120  # ~3,600 characters
    sources = [{"start_time": 12.0, "end_time": 24.0, "url": "https://example.com"}]

    # 1. Save long question
    cache_key = cache.save_answer(
        video_id="long_q_vid",
        question=long_question,
        answer="The system is effective because of deterministic retrieval.",
        sources=sources,
    )
    assert len(cache_key) == 64

    # 2. Retrieve long question
    cached = cache.get_cached_answer(
        video_id="long_q_vid",
        question=long_question,
    )
    assert cached is not None
    assert cached["answer"] == "The system is effective because of deterministic retrieval."
    assert len(cached["sources"]) == 1

    # 3. Upsert update with modified answer
    cache.save_answer(
        video_id="long_q_vid",
        question=long_question,
        answer="Updated answer for long question.",
        sources=sources,
    )
    cached_updated = cache.get_cached_answer(
        video_id="long_q_vid",
        question=long_question,
    )
    assert cached_updated["answer"] == "Updated answer for long question."


def test_atomic_upsert_concurrency():
    """
    Verify that concurrent saves for the exact same question and video succeed
    in PostgreSQL without race conditions or duplicate key crashes.
    """
    from app.database.database import engine as pg_engine
    from sqlalchemy import text
    from sqlalchemy.orm import sessionmaker

    if pg_engine.dialect.name != "postgresql":
        pytest.skip("Test requires PostgreSQL engine")

    question = "How does atomic upsert work under high concurrency?"
    video_id = "atomic_pg_vid_999"

    with pg_engine.connect() as conn:
        with conn.begin():
            conn.execute(
                text(f"""
                INSERT INTO videos (video_id, status, title)
                VALUES ('{video_id}', 'processed', 'Atomic PG Video')
                ON CONFLICT (video_id) DO NOTHING
            """)
            )

    PgSession = sessionmaker(bind=pg_engine)

    def worker(worker_id):
        session = PgSession()
        try:
            cache = CacheService(session)
            return cache.save_answer(
                video_id=video_id,
                question=question,
                answer=f"Answer from worker {worker_id}",
                sources=[{"worker": worker_id}],
            )
        finally:
            session.close()

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(worker, i) for i in range(5)]
            results = [f.result() for f in futures]

        assert len(results) == 5
        # All workers target the same deterministic key
        assert len(set(results)) == 1

        with pg_engine.connect() as conn:
            cnt = conn.execute(
                text(
                    f"SELECT count(*) FROM question_cache WHERE cache_key = '{results[0]}'"
                )
            ).scalar()
            assert cnt == 1
    finally:
        with pg_engine.connect() as conn:
            with conn.begin():
                conn.execute(
                    text(
                        f"DELETE FROM question_cache WHERE video_id = '{video_id}'"
                    )
                )
                conn.execute(
                    text(f"DELETE FROM videos WHERE video_id = '{video_id}'")
                )
