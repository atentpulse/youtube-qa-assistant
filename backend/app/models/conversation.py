from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database.database import Base


class Conversation(Base):

    __tablename__ = "conversations"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Scopes conversation strictly to a single YouTube video
    video_id = Column(
        String(20),
        ForeignKey("videos.video_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    title = Column(
        String(255),
        nullable=True,
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    user = relationship(
        "User",
        back_populates="conversations",
    )

    video = relationship(
        "Video",
        back_populates="conversations",
    )

    messages = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
    )

    @property
    def video_title(self) -> str | None:
        return self.video.title if self.video else None

    @property
    def message_count(self) -> int:
        return len(self.messages) if self.messages else 0
