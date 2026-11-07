import json
from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database.database import Base


class Message(Base):
    __tablename__ = "messages"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    conversation_id = Column(
        Integer,
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    role = Column(
        String(20),
        nullable=False,
    )

    content = Column(
        Text,
        nullable=False,
    )

    citations = Column(
        Text,
        nullable=True,
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    conversation = relationship(
        "Conversation",
        back_populates="messages",
    )

    @property
    def sources(self) -> list[dict]:
        """Deserialize citations JSON string into list of citation dicts for responses."""
        if not self.citations:
            return []
        try:
            parsed = json.loads(self.citations)
            return parsed if isinstance(parsed, list) else []
        except Exception:
            return []
