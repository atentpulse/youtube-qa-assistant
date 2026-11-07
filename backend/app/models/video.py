from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database.database import Base


class Video(Base):
    __tablename__ = "videos"

    id = Column(Integer, primary_key=True, index=True)

    video_id = Column(
        String(20),
        unique=True,
        nullable=False,
        index=True,
    )

    # user_id is now nullable to decouple canonical videos from a single owner
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    title = Column(
        String(500),
        nullable=True,
    )

    thumbnail_url = Column(
        String(1000),
        nullable=True,
    )

    status = Column(
        String(50),
        nullable=False,
        default="processing",
        server_default="processing",
    )

    segments = Column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    chunks = Column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    error_message = Column(
        String(1000),
        nullable=True,
    )

    processing_started_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Legacy relationship
    user = relationship(
        "User",
        back_populates="videos",
    )

    # Multi-user associations
    user_videos = relationship(
        "UserVideo",
        back_populates="video",
        cascade="all, delete-orphan",
    )

    # Associated conversations
    conversations = relationship(
        "Conversation",
        back_populates="video",
    )
