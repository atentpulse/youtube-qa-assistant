from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database.database import Base


class UserVideo(Base):
    __tablename__ = "user_videos"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    video_id = Column(
        String(20),
        ForeignKey("videos.video_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "video_id",
            name="uq_user_videos_user_video",
        ),
    )

    user = relationship(
        "User",
        back_populates="user_videos",
    )

    video = relationship(
        "Video",
        back_populates="user_videos",
    )
