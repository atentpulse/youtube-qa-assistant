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


class BugReport(Base):
    """Stores user-submitted bug reports, ingestion issues, and UI feedback."""

    __tablename__ = "bug_reports"

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

    title = Column(
        String(200),
        nullable=False,
    )

    description = Column(
        Text,
        nullable=False,
    )

    category = Column(
        String(50),
        nullable=False,
        default="general",
    )

    status = Column(
        String(20),
        nullable=False,
        default="open",
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    user = relationship("User", backref="bug_reports")
