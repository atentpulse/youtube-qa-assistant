from app.services.chunking_service import split_text, create_chunks
from app.services.youtube_service import extract_video_id
from app.utils.time_utils import format_timestamp, create_youtube_timestamp_url
import pytest


def test_extract_video_id():
    assert extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert extract_video_id("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert extract_video_id("https://www.youtube.com/shorts/dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    
    with pytest.raises(ValueError):
        extract_video_id("https://example.com/not_youtube")


def test_split_text():
    text = "word " * 100
    pieces = split_text(text, max_words=30)
    assert len(pieces) == 4
    assert len(pieces[0].split()) == 30


def test_create_chunks():
    segments = [
        {"text": "Hello world this is a test segment.", "start": 0.0, "duration": 5.0},
        {"text": "Another segment following closely.", "start": 5.0, "duration": 5.0},
    ]
    chunks = create_chunks(segments, max_words=50, overlap_words=10)
    assert len(chunks) == 1
    assert "Hello world" in chunks[0]["text"]
    assert chunks[0]["start_time"] == 0.0
    assert chunks[0]["end_time"] == 10.0


def test_time_utils():
    assert format_timestamp(65) == "01:05"
    assert format_timestamp(3665) == "01:01:05"
    url = create_youtube_timestamp_url("dQw4w9WgXcQ", 65.5)
    assert url == "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=65s"
