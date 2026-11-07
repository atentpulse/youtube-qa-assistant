from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator


VALID_CATEGORIES = {
    "general",
    "video_playback",
    "transcript_sync",
    "ai_qa",
    "ui_bug",
}


class BugReportCreate(BaseModel):
    title: str = Field(
        ...,
        min_length=3,
        max_length=200,
        description="Summary of the bug or issue (3-200 characters)",
    )
    description: str = Field(
        ...,
        min_length=10,
        max_length=5000,
        description="Detailed description of the issue and reproduction steps (10-5000 characters)",
    )
    category: str = Field(
        default="general",
        max_length=50,
        description="Category of the reported issue",
    )

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        trimmed = value.strip()
        if len(trimmed) < 3:
            raise ValueError("Title must be at least 3 characters long.")
        if len(trimmed) > 200:
            raise ValueError("Title cannot exceed 200 characters.")
        return trimmed

    @field_validator("description")
    @classmethod
    def validate_description(cls, value: str) -> str:
        trimmed = value.strip()
        if len(trimmed) < 10:
            raise ValueError("Description must be at least 10 characters long.")
        if len(trimmed) > 5000:
            raise ValueError("Description cannot exceed 5000 characters.")
        return trimmed

    @field_validator("category")
    @classmethod
    def validate_category(cls, value: str) -> str:
        cleaned = value.strip().lower()
        if not cleaned:
            return "general"
        if cleaned not in VALID_CATEGORIES:
            return "general"
        return cleaned


class BugReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    title: str
    description: str
    category: str
    status: str
    created_at: datetime
