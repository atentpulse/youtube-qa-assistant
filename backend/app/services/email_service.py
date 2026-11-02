import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi_mail import (
    ConnectionConfig,
    FastMail,
    MessageSchema,
    MessageType,
)

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parents[3]

load_dotenv(
    BASE_DIR / ".env"
)


class EmailService:

    def __init__(self):
        has_credentials = bool(
            os.getenv("MAIL_USERNAME") and os.getenv("MAIL_PASSWORD")
        )

        self.config = ConnectionConfig(
            MAIL_USERNAME=os.getenv("MAIL_USERNAME"),
            MAIL_PASSWORD=os.getenv("MAIL_PASSWORD"),
            MAIL_FROM=os.getenv("MAIL_FROM") or "noreply@vidmind.ai",
            MAIL_PORT=int(
                os.getenv(
                    "MAIL_PORT",
                    "587",
                )
            ),
            MAIL_SERVER=os.getenv(
                "MAIL_SERVER",
                "smtp.gmail.com",
            ),
            MAIL_STARTTLS=os.getenv(
                "MAIL_STARTTLS",
                "True",
            ).lower()
            == "true",
            MAIL_SSL_TLS=os.getenv(
                "MAIL_SSL_TLS",
                "False",
            ).lower()
            == "true",
            USE_CREDENTIALS=has_credentials,
            VALIDATE_CERTS=True,
        )

        if os.getenv("TESTING") == "1":
            self.fastmail = None
        elif self.config.USE_CREDENTIALS:
            self.fastmail = FastMail(self.config)
        else:
            self.fastmail = None

    @property
    def is_configured(self) -> bool:
        return self.fastmail is not None

    async def send_password_reset_email(
        self,
        email: str,
        reset_url: str,
    ) -> bool:
        message = MessageSchema(
            subject="Reset your YouTube Q&A Assistant password",
            recipients=[email],
            body=f"""
Hello,

We received a request to reset your password.

Click the link below to reset your password:

{reset_url}

This link will expire soon.

If you did not request a password reset,
you can safely ignore this email.

Regards,
YouTube Q&A Assistant
""",
            subtype=MessageType.plain,
        )

        if self.fastmail is not None:
            await self.fastmail.send_message(message)
            return True
        else:
            logger.info(
                "SMTP client not configured; skipped delivering password reset email to %s",
                email,
            )
            return False

    async def send_email_verification(
        self,
        email: str,
        verification_url: str,
    ) -> bool:
        message = MessageSchema(
            subject="Verify your YouTube Q&A Assistant email",
            recipients=[email],
            body=f"""
Hello,

Welcome to YouTube Q&A Assistant.

Please verify your email address by clicking the link below:

{verification_url}

This link will expire soon.

If you did not create this account,
you can safely ignore this email.

Regards,
YouTube Q&A Assistant
""",
            subtype=MessageType.plain,
        )

        if self.fastmail is not None:
            await self.fastmail.send_message(message)
            return True
        else:
            logger.info(
                "SMTP client not configured; skipped delivering verification email to %s",
                email,
            )
            return False
