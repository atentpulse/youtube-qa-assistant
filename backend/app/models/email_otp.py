from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.sql import func

from app.database.database import Base


class EmailOTP(Base):
    __tablename__ = "email_otps"

    id = Column(Integer, primary_key=True, index=True)

    email = Column(
        String(255),
        nullable=False,
        index=True,
    )

    otp_hash = Column(
        String(255),
        nullable=False,
    )

    expires_at = Column(
        DateTime(timezone=True),
        nullable=False,
    )

    attempts = Column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    max_attempts = Column(
        Integer,
        nullable=False,
        default=5,
        server_default="5",
    )

    used_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
