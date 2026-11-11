import os
import tempfile
from alembic.config import Config
from alembic import command
from sqlalchemy import create_engine, text


def test_upgrade_downgrade_cycle_disposable_db():
    temp_dir = tempfile.gettempdir()
    db_path = os.path.join(temp_dir, "ytgenius_test_migration_cycle.db")
    if os.path.exists(db_path):
        os.remove(db_path)

    db_url = f"sqlite:///{db_path}"
    alembic_ini_path = os.path.abspath("backend/alembic.ini")
    alembic_cfg = Config(alembic_ini_path)
    alembic_cfg.set_main_option("sqlalchemy.url", db_url)
    alembic_cfg.set_main_option("script_location", os.path.abspath("backend/alembic"))

    engine = create_engine(db_url)

    try:
        # 1. Create baseline schema at 0c2a55196561
        with engine.begin() as conn:
            conn.execute(text("""
                CREATE TABLE alembic_version (
                    version_num VARCHAR(32) NOT NULL,
                    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
                );
            """))
            conn.execute(text("INSERT INTO alembic_version VALUES ('0c2a55196561');"))
            conn.execute(text("""
                CREATE TABLE users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username VARCHAR(50) NOT NULL UNIQUE,
                    email VARCHAR(255) NOT NULL UNIQUE,
                    password_hash VARCHAR(255) NULL,
                    auth_provider VARCHAR(50) NOT NULL DEFAULT 'local',
                    email_verified BOOLEAN NOT NULL DEFAULT 0,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
            """))
            conn.execute(text("""
                CREATE TABLE videos (
                    video_id VARCHAR(20) PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    title VARCHAR(255) NOT NULL,
                    status VARCHAR(50) NOT NULL,
                    segments INTEGER NOT NULL DEFAULT 0,
                    chunks INTEGER NOT NULL DEFAULT 0,
                    thumbnail_url VARCHAR(500) NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                );
            """))
            conn.execute(text("""
                CREATE TABLE conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    title VARCHAR(255) NOT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                );
            """))
            conn.execute(text("""
                INSERT INTO users (id, username, email, password_hash, auth_provider, email_verified)
                VALUES (1, 'u1', 'u1@test.com', 'h1', 'local', 1);
            """))
            conn.execute(text("""
                INSERT INTO videos (video_id, user_id, title, status, segments, chunks)
                VALUES ('vid_existing', 1, 'Existing Vid', 'processed', 4, 2);
            """))

        # 2. Upgrade to d4f81a792e31
        command.upgrade(alembic_cfg, "d4f81a792e31")

        with engine.connect() as conn:
            uv = conn.execute(text("SELECT user_id, video_id FROM user_videos")).fetchall()
            assert len(uv) == 1
            assert uv[0] == (1, 'vid_existing')

        # 3. Add 2.0 multi-user shared data + orphan null video
        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO videos (video_id, user_id, title, status, segments, chunks)
                VALUES ('vid_shared_null', NULL, 'Shared Vid', 'processed', 8, 4),
                       ('vid_orphan', NULL, 'Orphan Vid', 'failed', 0, 0);
            """))
            conn.execute(text("""
                INSERT INTO user_videos (user_id, video_id, created_at)
                VALUES (1, 'vid_shared_null', '2026-11-01 10:00:00');
            """))

        # 4. Downgrade to 0c2a55196561
        command.downgrade(alembic_cfg, "0c2a55196561")

        with engine.connect() as conn:
            # Check all remaining videos have non-null user_id
            vids = conn.execute(text("SELECT video_id, user_id FROM videos")).fetchall()
            assert len(vids) == 2  # existing + shared (orphan deleted)
            for v in vids:
                assert v[1] is not None
            # Check shared video was backfilled with owner 1
            shared = [v for v in vids if v[0] == 'vid_shared_null']
            assert shared[0][1] == 1
            # Check user_videos is dropped
            tbls = [t[0] for t in conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'")).fetchall()]
            assert "user_videos" not in tbls

        # 5. Re-upgrade to head (d4f81a792e31)
        command.upgrade(alembic_cfg, "head")

        with engine.connect() as conn:
            tbls_after = [t[0] for t in conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'")).fetchall()]
            assert "user_videos" in tbls_after
            uv_after = conn.execute(text("SELECT user_id, video_id FROM user_videos")).fetchall()
            assert len(uv_after) >= 2

    finally:
        engine.dispose()
        if os.path.exists(db_path):
            try:
                os.remove(db_path)
            except Exception:
                pass
