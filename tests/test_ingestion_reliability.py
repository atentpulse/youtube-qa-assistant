from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from youtube_transcript_api import (
    NoTranscriptFound,
    TranscriptsDisabled,
)

from app.models.video import Video
from app.services.lock_service import VideoIngestionLock
from app.services.video_storage_service import VideoStorageService
from app.services.youtube_service import (
    TranscriptFetchError,
    fetch_transcript,
    format_transcript,
)


class DummySnippet:
    def __init__(self, text: str, start: float, duration: float):
        self.text = text
        self.start = start
        self.duration = duration


def test_fetch_transcript_manual_fallback():
    mock_api_instance = MagicMock()
    mock_list = MagicMock()
    mock_manual = MagicMock()
    mock_manual.fetch.return_value = [DummySnippet("manual caption", 0.0, 5.0)]
    mock_list.find_manually_created_transcript.return_value = mock_manual
    mock_api_instance.list.return_value = mock_list

    with patch("app.services.youtube_service.YouTubeTranscriptApi", return_value=mock_api_instance):
        res = fetch_transcript("test_vid_1")
        assert len(res) == 1
        assert res[0].text == "manual caption"


def test_fetch_transcript_generated_fallback():
    mock_api_instance = MagicMock()
    mock_list = MagicMock()
    # Manual raises NoTranscriptFound
    mock_list.find_manually_created_transcript.side_effect = NoTranscriptFound("test_vid_2", ["en"], mock_list)
    # Generated succeeds
    mock_gen = MagicMock()
    mock_gen.fetch.return_value = [DummySnippet("generated caption", 1.0, 4.0)]
    mock_list.find_generated_transcript.return_value = mock_gen
    mock_api_instance.list.return_value = mock_list

    with patch("app.services.youtube_service.YouTubeTranscriptApi", return_value=mock_api_instance):
        res = fetch_transcript("test_vid_2")
        assert len(res) == 1
        assert res[0].text == "generated caption"


def test_fetch_transcript_any_available_fallback():
    mock_api_instance = MagicMock()
    mock_list = MagicMock()
    mock_list.find_manually_created_transcript.side_effect = NoTranscriptFound("test_vid_3", ["en"], mock_list)
    mock_list.find_generated_transcript.side_effect = NoTranscriptFound("test_vid_3", ["en"], mock_list)
    mock_list.find_transcript.side_effect = NoTranscriptFound("test_vid_3", ["en"], mock_list)

    # Fallback to available tracks
    fallback_track = MagicMock()
    fallback_track.is_translatable = False
    fallback_track.fetch.return_value = [DummySnippet("fallback track caption", 0.0, 3.0)]
    mock_list.__iter__.return_value = [fallback_track]
    mock_api_instance.list.return_value = mock_list

    with patch("app.services.youtube_service.YouTubeTranscriptApi", return_value=mock_api_instance):
        res = fetch_transcript("test_vid_3")
        assert len(res) == 1
        assert res[0].text == "fallback track caption"


def test_fetch_transcript_disabled_raises_error():
    mock_api_instance = MagicMock()
    mock_api_instance.list.side_effect = TranscriptsDisabled("test_vid_disabled")

    with patch("app.services.youtube_service.YouTubeTranscriptApi", return_value=mock_api_instance):
        with pytest.raises(TranscriptFetchError) as exc_info:
            fetch_transcript("test_vid_disabled", retries=1)
        assert "disabled" in str(exc_info.value).lower()


def test_format_transcript_compatibility():
    # Test dictionary input
    dict_items = [
        {"text": "Line 1\nwith break", "start": 1.2, "duration": 3.4},
        {"text": "  Line 2 with spaces  ", "start": 4.6, "duration": 2.0},
    ]
    formatted_dicts = format_transcript(dict_items)
    assert formatted_dicts == [
        {"text": "Line 1 with break", "start": 1.2, "duration": 3.4},
        {"text": "Line 2 with spaces", "start": 4.6, "duration": 2.0},
    ]

    # Test object input
    obj_items = [
        DummySnippet("Snippet 1\ntext", 0.0, 2.5),
        DummySnippet("Snippet 2", 2.5, 3.0),
    ]
    formatted_objs = format_transcript(obj_items)
    assert formatted_objs == [
        {"text": "Snippet 1 text", "start": 0.0, "duration": 2.5},
        {"text": "Snippet 2", "start": 2.5, "duration": 3.0},
    ]


def test_recover_stale_jobs_without_lock(db, test_user):
    storage = VideoStorageService(db)
    old_time = datetime.now(timezone.utc) - timedelta(minutes=25)

    video = Video(
        video_id="stale_video_1",
        user_id=test_user.id,
        status="processing",
        processing_started_at=old_time,
        created_at=old_time,
        updated_at=old_time,
    )
    db.add(video)
    db.commit()

    recovered = storage.recover_stale_jobs(max_age_minutes=15)
    assert "stale_video_1" in recovered

    db.refresh(video)
    assert video.status == "failed"
    assert "timed out after 15 minutes" in video.error_message


def test_recover_stale_jobs_with_active_lock_preserved(db, test_user):
    storage = VideoStorageService(db)
    old_time = datetime.now(timezone.utc) - timedelta(minutes=25)

    video = Video(
        video_id="locked_active_video",
        user_id=test_user.id,
        status="processing",
        processing_started_at=old_time,
        created_at=old_time,
        updated_at=old_time,
    )
    db.add(video)
    db.commit()

    # Worker currently holds the lock
    lock = VideoIngestionLock(db, "locked_active_video")
    acquired = lock.acquire()
    assert acquired is True

    try:
        recovered = storage.recover_stale_jobs(max_age_minutes=15)
        assert "locked_active_video" not in recovered

        db.refresh(video)
        # Status must remain 'processing' since worker is actively alive
        assert video.status == "processing"
        assert video.error_message is None
    finally:
        lock.release()


def test_create_or_update_error_recording_and_retry_clearing(db, test_user):
    storage = VideoStorageService(db)

    # 1. Initial creation with failure
    failed_vid = storage.create_or_update_video(
        video_id="lifecycle_vid",
        user_id=test_user.id,
        status="failed",
        error_message="Network timeout during chunk embedding",
    )
    assert failed_vid["status"] == "failed"
    assert failed_vid["error_message"] == "Network timeout during chunk embedding"

    # 2. User retries processing -> error cleared, processing_started_at set
    retrying_vid = storage.create_or_update_video(
        video_id="lifecycle_vid",
        user_id=test_user.id,
        status="processing",
    )
    assert retrying_vid["status"] == "processing"
    assert retrying_vid["error_message"] is None
    assert retrying_vid["processing_started_at"] is not None

    # 3. Processing completes successfully -> error cleared
    completed_vid = storage.create_or_update_video(
        video_id="lifecycle_vid",
        user_id=test_user.id,
        status="processed",
        segments=12,
        chunks=6,
    )
    assert completed_vid["status"] == "processed"
    assert completed_vid["error_message"] is None
    assert completed_vid["segments"] == 12
    assert completed_vid["chunks"] == 6
