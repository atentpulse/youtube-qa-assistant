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

@pytest.mark.asyncio
async def test_qdrant_add_documents_batching_and_timeout():
    import numpy as np
    from unittest.mock import MagicMock
    from app.services.qdrant_service import QdrantVectorStore

    # 1. Verify timeout configured on remote client
    qs = QdrantVectorStore(url="http://mock-qdrant:6333", api_key="fake-key", timeout=45.0)
    assert qs.client._client._timeout == 45

    # 2. Test batching in add_documents
    mock_client = MagicMock()
    qs.client = mock_client

    # Create 84 dummy chunks and embeddings (matching aZglGvBPQGs)
    dummy_chunks = [
        {
            "video_id": "test_batch_vid",
            "text": f"Chunk content {i}",
            "start_time": float(i * 10),
            "end_time": float((i + 1) * 10),
        }
        for i in range(84)
    ]
    dummy_embeddings = np.zeros((84, 384))

    qs.add_documents(dummy_embeddings, dummy_chunks, batch_size=64)

    # 84 chunks with batch_size=64 must result in 2 calls to upsert (64 points, then 20 points)
    assert mock_client.upsert.call_count == 2
    batch1 = mock_client.upsert.call_args_list[0][1]["points"]
    batch2 = mock_client.upsert.call_args_list[1][1]["points"]
    assert len(batch1) == 64
    assert len(batch2) == 20
    assert batch1[0].payload["video_id"] == "test_batch_vid"


def test_rag_process_video_background_timeout_failure_handling(db, test_user, monkeypatch):
    from unittest.mock import MagicMock, patch
    from app.services.rag_service import RAGService
    from app.services.video_storage_service import VideoStorageService
    from app.models.video import Video
    import app.services.rag_service as rag_service_mod

    storage = VideoStorageService(db)
    storage.create_or_update_video(
        video_id="timeout_vid_123",
        user_id=test_user.id,
        status="processing",
        title="Timeout Test",
    )

    rag = RAGService()
    # Mock transcript fetching and embedding so we isolate add_documents
    monkeypatch.setattr(rag_service_mod, "fetch_transcript", lambda vid: [{"text": "sample", "start": 0.0, "duration": 5.0}])
    monkeypatch.setattr(rag_service_mod, "format_transcript", lambda t: [{"text": "sample", "start": 0.0, "duration": 5.0}])
    monkeypatch.setattr(rag_service_mod, "create_chunks", lambda s, max_words=180: [{"text": "sample", "start_time": 0.0, "end_time": 5.0}])
    rag.embedding_service.embed_documents = MagicMock(return_value=[[0.1] * 384])

    # Mock add_documents to simulate remote write timeout
    rag.vector_store.add_documents = MagicMock(side_effect=TimeoutError("The write operation timed out"))
    rag.vector_store.video_exists = MagicMock(return_value=False)

    monkeypatch.setattr(rag_service_mod, "SessionLocal", lambda: db)

    # Must catch exception gracefully and not raise
    with patch.object(rag_service_mod.logger, "error", wraps=rag_service_mod.logger.error) as mock_log_error:
        rag.process_video_background("timeout_vid_123", test_user.id)

    # Verify video was marked failed in DB
    db.expire_all()
    vid = db.query(Video).filter(Video.video_id == "timeout_vid_123").first()
    assert vid.status == "failed"

    # Verify exception was logged without being swallowed and recorded in DB
    assert mock_log_error.called
    call_args = mock_log_error.call_args[0]
    assert any("timeout_vid_123" in str(arg) for arg in call_args)
    assert vid.error_message and "The write operation timed out" in vid.error_message


def test_failed_video_can_be_retried(db, test_user):
    from unittest.mock import MagicMock
    from app.services.rag_service import RAGService
    from app.services.video_storage_service import VideoStorageService
    from app.models.video import Video

    storage = VideoStorageService(db)
    storage.create_or_update_video(
        video_id="retry_vid_456",
        user_id=test_user.id,
        status="failed",
        title="Failed Video",
    )

    rag = RAGService()
    # Retrying a failed video must return status="processing" to trigger ingestion
    result = rag.process_video(
        db=db,
        user_id=test_user.id,
        url="https://www.youtube.com/watch?v=retry_vid_456",
        force_reprocess=False,
    )
    assert result["status"] == "processing"

    # In DB, video status should now be updated to processing
    db.expire_all()
    vid = db.query(Video).filter(Video.video_id == "retry_vid_456").first()
    assert vid.status == "processing"

