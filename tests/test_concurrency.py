import threading
import time
from unittest.mock import MagicMock, patch
import pytest
from sqlalchemy.orm import Session

from app.services.lock_service import VideoIngestionLock, video_id_to_lock_id
from app.services.rag_service import RAGService


def test_video_id_to_lock_id_deterministic():
    id1 = video_id_to_lock_id("dQw4w9WgXcQ")
    id2 = video_id_to_lock_id("dQw4w9WgXcQ")
    id3 = video_id_to_lock_id("other_video_id")

    assert isinstance(id1, int)
    assert id1 == id2
    assert id1 != id3
    # Check within 64-bit signed integer range
    assert -(2**63) <= id1 < 2**63


def test_lock_mutual_exclusion_and_release(db: Session):
    vid = "test_vid_concurrency_1"

    lock1 = VideoIngestionLock(db, vid)
    lock2 = VideoIngestionLock(db, vid)

    # 1. First lock acquires
    assert lock1.acquire() is True
    assert VideoIngestionLock.is_locked(db, vid) is True

    # 2. Second lock cannot acquire while held
    assert lock2.acquire() is False

    # 3. First lock releases
    assert lock1.release() is True

    # 4. Now second lock can acquire
    assert lock2.acquire() is True
    assert VideoIngestionLock.is_locked(db, vid) is True

    # 5. Clean release
    assert lock2.release() is True
    assert VideoIngestionLock.is_locked(db, vid) is False


def test_lock_different_videos_independent(db: Session):
    vid_a = "video_alpha"
    vid_b = "video_beta"

    lock_a = VideoIngestionLock(db, vid_a)
    lock_b = VideoIngestionLock(db, vid_b)

    assert lock_a.acquire() is True
    assert lock_b.acquire() is True

    assert VideoIngestionLock.is_locked(db, vid_a) is True
    assert VideoIngestionLock.is_locked(db, vid_b) is True

    assert lock_a.release() is True
    assert VideoIngestionLock.is_locked(db, vid_a) is False
    assert VideoIngestionLock.is_locked(db, vid_b) is True

    assert lock_b.release() is True
    assert VideoIngestionLock.is_locked(db, vid_b) is False


def test_lock_context_manager(db: Session):
    vid = "test_vid_context"

    with VideoIngestionLock(db, vid) as lock:
        assert lock._acquired is True
        assert VideoIngestionLock.is_locked(db, vid) is True

    assert VideoIngestionLock.is_locked(db, vid) is False


def test_concurrent_threads_single_winner(db: Session):
    vid = "test_vid_threads"
    results = []
    barrier = threading.Barrier(10)

    def worker():
        barrier.wait()
        lock = VideoIngestionLock(db, vid)
        acquired = lock.acquire()
        results.append((acquired, lock))
        if acquired:
            time.sleep(0.05)  # Hold briefly
            lock.release()

    threads = [threading.Thread(target=worker) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # Exactly one thread should have acquired the lock
    acquired_count = sum(1 for acq, _ in results if acq)
    assert acquired_count == 1
    # After all threads finished, lock is free
    assert VideoIngestionLock.is_locked(db, vid) is False


def test_rag_process_video_detects_active_lock(db: Session):
    rag = RAGService()
    vid = "active_lock_vid"
    url = f"https://www.youtube.com/watch?v={vid}"

    # Hold the lock via VideoIngestionLock
    lock = VideoIngestionLock(db, vid)
    assert lock.acquire() is True

    try:
        # Calling process_video while lock is held should return already_processing
        res = rag.process_video(db=db, user_id=1, url=url)
        assert res["status"] == "already_processing"
        assert res["video_id"] == vid
    finally:
        lock.release()


def test_rag_process_video_background_skips_when_locked(db: Session):
    rag = RAGService()
    vid = "bg_lock_vid"

    # Pre-acquire the lock
    lock = VideoIngestionLock(db, vid)
    assert lock.acquire() is True

    try:
        with patch.object(rag, "embedding_service") as mock_embed, \
             patch("app.services.rag_service.fetch_transcript") as mock_trans:
            # Run background task
            rag.process_video_background(vid, user_id=1)
            # Transcript and embedding should NOT have been called because lock was held
            mock_trans.assert_not_called()
            mock_embed.embed_documents.assert_not_called()
    finally:
        lock.release()
