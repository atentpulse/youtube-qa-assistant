from datetime import datetime

from pydantic import BaseModel, Field


class ProcessVideoRequest(BaseModel):

    url: str = Field(
        ...,
        min_length=10,
        max_length=500,
        description="YouTube video URL",
    )

    force_reprocess: bool = False


class ProcessVideoResponse(BaseModel):

    video_id: str

    segments: int = 0

    chunks: int = 0

    status: str


class VideoStatusResponse(BaseModel):

    video_id: str

    title: str | None = None

    thumbnail_url: str | None = None

    status: str

    segments: int

    chunks: int

    error_message: str | None = None

    processing_started_at: datetime | None = None


class VideoListItem(BaseModel):

    video_id: str

    title: str | None = None

    thumbnail_url: str | None = None

    status: str

    segments: int

    chunks: int

    error_message: str | None = None

    processing_started_at: datetime | None = None

    created_at: datetime | None = None
    updated_at: datetime | None = None


class VideoListResponse(BaseModel):

    videos: list[VideoListItem]

    total: int
