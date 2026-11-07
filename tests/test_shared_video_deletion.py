import pytest
from sqlalchemy import text
from app.models.user import User
from app.models.video import Video
from app.models.user_video import UserVideo
from app.services.auth_service import AuthService
from app.services.video_storage_service import VideoStorageService
from app.database.database import engine as pg_engine


@pytest.mark.asyncio
async def test_account_deletion_flow_preserves_shared_canonical_video(
    async_client, db, test_user, test_user_2
):
    """
    Test A: Verify that when User A deletes their account via the /auth/me
    deletion flow, a canonical video shared with User B is NOT deleted,
    and User B's library association remains intact.
    """
    storage = VideoStorageService(db)
    shared_vid = "shared_flow_vid_101"

    # 1. User A creates canonical video
    storage.create_or_update_video(
        video_id=shared_vid,
        user_id=test_user.id,
        status="processed",
        title="Shared Video Account Deletion Test",
    )

    # 2. User B links to canonical video
    storage.link_user_to_video(test_user_2.id, shared_vid)

    # Verify initial setup
    assert storage.has_other_references(shared_vid, exclude_user_id=test_user.id) is True
    assert db.query(UserVideo).filter_by(user_id=test_user.id, video_id=shared_vid).first() is not None
    assert db.query(UserVideo).filter_by(user_id=test_user_2.id, video_id=shared_vid).first() is not None

    # 3. Create auth headers for User A and execute account deletion flow
    from app.auth.jwt import create_access_token
    token_a = create_access_token(user_id=test_user.id)
    headers_a = {"Authorization": f"Bearer {token_a}"}

    response = await async_client.delete("/auth/me", headers=headers_a)
    assert response.status_code == 200
    assert response.json()["message"] == "Account deleted successfully."

    # 4. Verify User A is deleted
    assert db.query(User).filter_by(id=test_user.id).first() is None

    # 5. Verify canonical video STILL exists in the database
    canonical = db.query(Video).filter_by(video_id=shared_vid).first()
    assert canonical is not None, "Canonical video must survive User A account deletion!"
    assert canonical.user_id is None, "Video user_id should be set to None"

    # 6. Verify User B's library association is completely preserved
    u2_link = db.query(UserVideo).filter_by(user_id=test_user_2.id, video_id=shared_vid).first()
    assert u2_link is not None, "User B's library link must remain intact!"

    u2_access = storage.get_video(shared_vid, test_user_2.id)
    assert u2_access is not None
    assert u2_access["title"] == "Shared Video Account Deletion Test"


@pytest.mark.asyncio
async def test_direct_orm_deletion_preserves_shared_canonical_video(
    db, test_user, test_user_2
):
    """
    Test B: Verify that direct SQLAlchemy ORM deletion of User A (db.delete(user))
    does not cascade-delete the shared canonical video or User B's association.
    """
    storage = VideoStorageService(db)
    shared_vid = "shared_orm_vid_202"

    # User A creates video
    storage.create_or_update_video(
        video_id=shared_vid,
        user_id=test_user.id,
        status="processed",
        title="Shared ORM Test",
    )
    # User B links video
    storage.link_user_to_video(test_user_2.id, shared_vid)

    # Directly delete user via SQLAlchemy session without helper methods
    db.delete(test_user)
    db.commit()

    # User A is gone
    assert db.query(User).filter_by(id=test_user.id).first() is None

    # Canonical video must still exist
    canonical = db.query(Video).filter_by(video_id=shared_vid).first()
    assert canonical is not None, "ORM cascade must not delete canonical video on user deletion!"

    # User B still has access
    assert db.query(UserVideo).filter_by(user_id=test_user_2.id, video_id=shared_vid).first() is not None
    assert storage.get_video(shared_vid, test_user_2.id) is not None


def test_postgresql_foreign_key_delete_set_null():
    """
    Test C: Verify against real PostgreSQL database that the fk_videos_user_id
    foreign key constraint has delete_rule = 'SET NULL' and raw SQL DELETE FROM users
    sets videos.user_id = NULL without deleting the canonical video or other users' user_videos.
    Runs inside a transaction that is rolled back immediately.
    """
    if pg_engine.dialect.name != "postgresql":
        pytest.skip("Test requires PostgreSQL engine")

    with pg_engine.connect() as conn:
        with conn.begin():
            # 1. Verify foreign key metadata
            constraint_info = conn.execute(text("""
                SELECT rc.delete_rule
                FROM information_schema.table_constraints AS tc
                JOIN information_schema.referential_constraints AS rc
                  ON tc.constraint_name = rc.constraint_name
                  AND tc.table_schema = rc.constraint_schema
                WHERE tc.table_name = 'videos'
                  AND tc.constraint_name = 'fk_videos_user_id'
            """)).scalar()

            assert constraint_info == "SET NULL", (
                f"Expected fk_videos_user_id delete_rule to be 'SET NULL', got '{constraint_info}'"
            )

            # 2. Insert test data
            u1_id = conn.execute(text("""
                INSERT INTO users (username, email, auth_provider, email_verified)
                VALUES ('pg_test_u1', 'pg_test_u1@example.com', 'local', true)
                RETURNING id
            """)).scalar()

            u2_id = conn.execute(text("""
                INSERT INTO users (username, email, auth_provider, email_verified)
                VALUES ('pg_test_u2', 'pg_test_u2@example.com', 'local', true)
                RETURNING id
            """)).scalar()

            test_vid = "pg_cascade_vid_303"
            conn.execute(text(f"""
                INSERT INTO videos (video_id, user_id, status, title)
                VALUES ('{test_vid}', {u1_id}, 'processed', 'PostgreSQL Cascade Test')
            """))

            conn.execute(text(f"""
                INSERT INTO user_videos (user_id, video_id)
                VALUES ({u2_id}, '{test_vid}')
            """))

            # 3. Raw SQL deletion of User 1
            conn.execute(text(f"DELETE FROM users WHERE id = {u1_id}"))

            # 4. Assert video still exists and user_id is NULL
            vid_row = conn.execute(text(f"""
                SELECT video_id, user_id FROM videos WHERE video_id = '{test_vid}'
            """)).first()

            assert vid_row is not None, "Canonical video must survive raw SQL user deletion in PostgreSQL!"
            assert vid_row[1] is None, "PostgreSQL foreign key must set videos.user_id = NULL!"

            # 5. Assert User 2's library association remains intact
            uv_row = conn.execute(text(f"""
                SELECT user_id, video_id FROM user_videos WHERE user_id = {u2_id} AND video_id = '{test_vid}'
            """)).first()

            assert uv_row is not None, "User 2 user_videos entry must survive User 1 deletion in PostgreSQL!"

            # 6. Explicit rollback so zero rows persist
            conn.rollback()


@pytest.mark.asyncio
async def test_unreferenced_canonical_video_cleanup_when_last_user_deletes(
    db, test_user, test_user_2
):
    """
    Test D: Verify that when multiple users share a video, unlinking one user
    preserves the canonical video, but when the LAST referencing user deletes it,
    the canonical video row is safely purged.
    """
    storage = VideoStorageService(db)
    shared_vid = "cleanup_last_user_vid_404"

    # Create video shared by User 1 and User 2
    storage.create_or_update_video(
        video_id=shared_vid,
        user_id=test_user.id,
        status="processed",
        title="Final Cleanup Test",
    )
    storage.link_user_to_video(test_user_2.id, shared_vid)

    # User 1 deletes
    assert storage.has_other_references(shared_vid, exclude_user_id=test_user.id) is True
    deleted_u1 = storage.delete_video(shared_vid, test_user.id)
    assert deleted_u1 is True

    # User 1 has no access, but User 2 still does, and canonical video exists
    assert storage.get_video(shared_vid, test_user.id) is None
    assert storage.get_video(shared_vid, test_user_2.id) is not None
    assert db.query(Video).filter_by(video_id=shared_vid).first() is not None

    # User 2 (last user) deletes
    assert storage.has_other_references(shared_vid, exclude_user_id=test_user_2.id) is False
    deleted_u2 = storage.delete_video(shared_vid, test_user_2.id)
    assert deleted_u2 is True

    # Now canonical video is completely purged
    assert storage.get_video(shared_vid, test_user_2.id) is None
    assert db.query(Video).filter_by(video_id=shared_vid).first() is None
