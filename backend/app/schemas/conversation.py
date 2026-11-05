from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CreateConversationRequest(BaseModel):

    title: str | None = None

    video_id: str | None = None


class ConversationResponse(BaseModel):

    model_config = ConfigDict(from_attributes=True)

    id: int

    title: str | None

    video_id: str | None = None

    created_at: datetime

    updated_at: datetime


class MessageResponse(BaseModel):

    model_config = ConfigDict(from_attributes=True)

    id: int

    role: str

    content: str

    created_at: datetime


class ConversationDetailResponse(
    ConversationResponse
):

    messages: list[MessageResponse]


class UpdateConversationRequest(BaseModel):

    title: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="New conversation title",
    )


class PaginatedMessagesResponse(BaseModel):

    messages: list[MessageResponse]

    next_cursor: int | None


class SendMessageRequest(BaseModel):

    content: str | None = None

    question: str | None = None

    video_id: str | None = None

    answer_length: str | None = "balanced"

    response_style: str | None = "explanatory"

    prefer_structured: bool | None = True

    include_examples: bool | None = False


class SendMessageResponse(BaseModel):

    model_config = ConfigDict(from_attributes=True)

    id: int

    conversation_id: int

    role: str

    content: str

    sources: list[dict] = []

    created_at: datetime
