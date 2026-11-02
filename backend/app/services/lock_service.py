import hashlib
import logging
import threading
from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Fallback locks for SQLite (in-memory test environments)
_sqlite_fallback_locks: dict[str, threading.Lock] = {}
_sqlite_global_lock = threading.Lock()


def video_id_to_lock_id(video_id: str) -> int:
    """Generate a deterministic signed 64-bit integer lock ID from video_id for PostgreSQL."""
    digest = hashlib.sha256(video_id.encode("utf-8")).digest()[:8]
    return int.from_bytes(digest, byteorder="big", signed=True)


class VideoIngestionLock:
    """
    Distributed advisory lock coordinator for YouTube video ingestion.
    Uses PostgreSQL session-level advisory locks (pg_try_advisory_lock)
    to prevent duplicate transcription, chunking, and vector ingestion across workers.
    Falls back to a thread-safe lock when running against SQLite in test suites.
    """

    def __init__(self, db: Session, video_id: str):
        self.db = db
        self.video_id = video_id.strip()
        self.lock_id = video_id_to_lock_id(self.video_id)
        self.is_postgresql = bool(
            self.db.bind and self.db.bind.dialect.name == "postgresql"
        )
        self._acquired = False
        self._sqlite_lock = None

    def acquire(self) -> bool:
        """Attempt to acquire the advisory lock non-blockingly."""
        if self._acquired:
            return True

        if self.is_postgresql:
            try:
                # Use raw DB connection for session-level advisory lock
                result = self.db.execute(
                    text("SELECT pg_try_advisory_lock(:lock_id)"),
                    {"lock_id": self.lock_id},
                ).scalar()
                self._acquired = bool(result)
                if self._acquired:
                    logger.info(
                        "Acquired PostgreSQL advisory lock for video %s (lock_id=%d)",
                        self.video_id,
                        self.lock_id,
                    )
                else:
                    logger.info(
                        "Video %s is currently locked by another worker",
                        self.video_id,
                    )
                return self._acquired
            except Exception as exc:
                logger.error(
                    "Failed to acquire PostgreSQL advisory lock for %s: %s",
                    self.video_id,
                    exc,
                )
                return False
        else:
            # SQLite fallback for test harness
            with _sqlite_global_lock:
                if self.video_id not in _sqlite_fallback_locks:
                    _sqlite_fallback_locks[self.video_id] = threading.Lock()
                self._sqlite_lock = _sqlite_fallback_locks[self.video_id]

            self._acquired = self._sqlite_lock.acquire(blocking=False)
            return self._acquired

    def release(self) -> bool:
        """Release the held advisory lock."""
        if not self._acquired:
            return False

        if self.is_postgresql:
            try:
                try:
                    result = self.db.execute(
                        text("SELECT pg_advisory_unlock(:lock_id)"),
                        {"lock_id": self.lock_id},
                    ).scalar()
                except Exception:
                    # Clear pending transaction rollback state if needed to execute unlock
                    self.db.rollback()
                    result = self.db.execute(
                        text("SELECT pg_advisory_unlock(:lock_id)"),
                        {"lock_id": self.lock_id},
                    ).scalar()
                self._acquired = False
                logger.info(
                    "Released PostgreSQL advisory lock for video %s",
                    self.video_id,
                )
                return bool(result)
            except Exception as exc:
                logger.error(
                    "Failed to release PostgreSQL advisory lock for %s: %s",
                    self.video_id,
                    exc,
                )
                self._acquired = False
                return False
        else:
            if self._sqlite_lock:
                try:
                    self._sqlite_lock.release()
                except RuntimeError:
                    pass
            self._acquired = False
            return True

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()

    @classmethod
    def is_locked(cls, db: Session, video_id: str) -> bool:
        """Check if an advisory lock is currently held on this video_id."""
        video_id = video_id.strip()
        lock_id = video_id_to_lock_id(video_id)
        is_postgresql = bool(db.bind and db.bind.dialect.name == "postgresql")
        if is_postgresql:
            try:
                unsigned_64 = lock_id & 0xFFFFFFFFFFFFFFFF
                high_32 = (unsigned_64 >> 32) & 0xFFFFFFFF
                low_32 = unsigned_64 & 0xFFFFFFFF
                res = db.execute(
                    text(
                        "SELECT 1 FROM pg_locks "
                        "WHERE locktype = 'advisory' "
                        "AND classid::bigint = :high AND objid::bigint = :low"
                    ),
                    {"high": high_32, "low": low_32},
                ).scalar()
                return bool(res)
            except Exception as exc:
                logger.error("Error checking advisory lock status: %s", exc)
                return False
        else:
            with _sqlite_global_lock:
                lock = _sqlite_fallback_locks.get(video_id)
                return lock.locked() if lock else False
