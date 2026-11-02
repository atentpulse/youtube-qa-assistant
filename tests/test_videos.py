import pytest
from app.models.video import Video
from app.models.user_video import UserVideo
from app.services.video_storage_service import VideoStorageService


@pytest.mark.asyncio
async def test_process_video_endpoint(async_client, auth_headers, mock_rag_service):
    mock_rag_service.process_video.return_value = {
        "video_id": "test_vid_123",
        "segments": 0,
        "chunks": 0,
        "status": "processing",
    }

    response = await async_client.post(
        "/videos/process",
        headers=auth_headers,
        json={"url": "https://www.youtube.com/watch?v=test_vid_123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["video_id"] == "test_vid_123"
    assert data["status"] == "processing"


@pytest.mark.asyncio
async def test_canonical_video_multi_user_reuse(db, test_user, test_user_2):
    storage = VideoStorageService(db)

    # 1. User 1 creates and completes video processing
    vid = storage.create_or_update_video(
        video_id="canonical_123",
        user_id=test_user.id,
        status="processed",
        segments=10,
        chunks=5,
        title="Sample Video",
        thumbnail_url="https://img.youtube.com/vi/canonical_123/0.jpg",
    )
    assert vid["status"] == "processed"

    # User 1 has the video
    assert storage.get_video("canonical_123", test_user.id) is not None
    # User 2 does not have it yet
    assert storage.get_video("canonical_123", test_user_2.id) is None

    # 2. User 2 links/adds the same video
    canonical = storage.get_canonical_video("canonical_123")
    assert canonical is not None
    assert canonical["status"] == "processed"

    # Link User 2
    storage.link_user_to_video(test_user_2.id, "canonical_123")

    # Now both users have access to the same canonical video
    u1_vid = storage.get_video("canonical_123", test_user.id)
    u2_vid = storage.get_video("canonical_123", test_user_2.id)
    assert u1_vid is not None
    assert u2_vid is not None
    assert u1_vid["title"] == u2_vid["title"]

    # Only 1 canonical Video row exists in the database
    canonical_count = db.query(Video).filter(Video.video_id == "canonical_123").count()
    assert canonical_count == 1

    # 2 UserVideo rows exist
    user_links = db.query(UserVideo).filter(UserVideo.video_id == "canonical_123").count()
    assert user_links == 2


@pytest.mark.asyncio
async def test_reference_counted_safe_deletion(db, test_user, test_user_2):
    storage = VideoStorageService(db)

    # Create canonical video shared by both users
    storage.create_or_update_video(
        video_id="shared_vid_999",
        user_id=test_user.id,
        status="processed",
        segments=20,
        chunks=8,
        title="Shared Video",
    )
    storage.link_user_to_video(test_user_2.id, "shared_vid_999")

    # Verify both users have it
    assert storage.has_other_references("shared_vid_999", exclude_user_id=test_user.id) is True

    # User 1 deletes the video
    deleted = storage.delete_video("shared_vid_999", test_user.id)
    assert deleted is True

    # User 1 no longer has access
    assert storage.get_video("shared_vid_999", test_user.id) is None

    # User 2 STILL has access because canonical record was preserved!
    u2_vid = storage.get_video("shared_vid_999", test_user_2.id)
    assert u2_vid is not None
    assert u2_vid["title"] == "Shared Video"

    # Canonical record still exists in the database
    canonical = db.query(Video).filter(Video.video_id == "shared_vid_999").first()
    assert canonical is not None

    # User 2 now deletes the video
    assert storage.has_other_references("shared_vid_999", exclude_user_id=test_user_2.id) is False
    deleted_u2 = storage.delete_video("shared_vid_999", test_user_2.id)
    assert deleted_u2 is True

    # Now canonical record is completely purged
    canonical_after = db.query(Video).filter(Video.video_id == "shared_vid_999").first()
    assert canonical_after is None


@pytest.mark.asyncio
async def test_get_video_status_endpoint(async_client, db, test_user, auth_headers, auth_headers_2):
    storage = VideoStorageService(db)
    storage.create_or_update_video(
        video_id="status_vid_555",
        user_id=test_user.id,
        status="processed",
        segments=15,
        chunks=6,
        title="Status Test",
    )

    # User 1 checks status
    resp = await async_client.get("/videos/status_vid_555/status", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["video_id"] == "status_vid_555"
    assert data["status"] == "processed"
    assert data["segments"] == 15
    assert data["chunks"] == 6

    # User 2 checks status -> 404 Not Found (isolated)
    resp_u2 = await async_client.get("/videos/status_vid_555/status", headers=auth_headers_2)
    assert resp_u2.status_code == 404


@pytest.mark.asyncio
async def test_list_videos_endpoint(async_client, db, test_user, test_user_2, auth_headers, auth_headers_2):
    storage = VideoStorageService(db)
    storage.create_or_update_video(
        video_id="user1_only",
        user_id=test_user.id,
        status="processed",
        title="User 1 Video",
    )
    storage.create_or_update_video(
        video_id="user2_only",
        user_id=test_user_2.id,
        status="processed",
        title="User 2 Video",
    )

    # User 1 list
    resp1 = await async_client.get("/videos", headers=auth_headers)
    assert resp1.status_code == 200
    vids1 = resp1.json()["videos"]
    video_ids1 = [v["video_id"] for v in vids1]
    assert "user1_only" in video_ids1
    assert "user2_only" not in video_ids1

    # User 2 list
    resp2 = await async_client.get("/videos", headers=auth_headers_2)
    assert resp2.status_code == 200
    vids2 = resp2.json()["videos"]
    video_ids2 = [v["video_id"] for v in vids2]
    assert "user2_only" in video_ids2
    assert "user1_only" not in video_ids2
