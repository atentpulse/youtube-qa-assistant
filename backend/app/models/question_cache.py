from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func

from app.database.database import Base


class QuestionCache(Base):
    __tablename__ = "question_cache"

    id = Column(Integer, primary_key=True, index=True)

    cache_key = Column(
        String(64),
        unique=True,
        index=True,
        nullable=False,
    )

    video_id = Column(
        String(20),
        ForeignKey("videos.video_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    question = Column(
        Text,
        nullable=False,
    )

    answer = Column(
        Text,
        nullable=False,
    )

    sources = Column(
        Text,
        nullable=False,
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
