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
from fastapi_mail.errors import ConnectionErrors

from app.core import settings

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parents[3]

load_dotenv(
    BASE_DIR / ".env"
)


class EmailService:

    def __init__(self):
        raw_username = settings.MAIL_USERNAME or os.getenv("MAIL_USERNAME")
        mail_username = raw_username.strip() if raw_username else None
        raw_password = settings.MAIL_PASSWORD or os.getenv("MAIL_PASSWORD")
        # Sanitize whitespace/spaces from passwords (such as Google 4x4 app passwords)
        mail_password = raw_password.strip().replace(" ", "") if raw_password else None
        raw_from = settings.MAIL_FROM or os.getenv("MAIL_FROM") or "noreply@ytgenius.ai"
        mail_from = raw_from.strip()
        raw_server = settings.MAIL_SERVER or os.getenv("MAIL_SERVER") or "smtp.gmail.com"
        mail_server = raw_server.strip()

        try:
            port_val = settings.MAIL_PORT or os.getenv("MAIL_PORT") or "587"
            mail_port = int(port_val)
        except (ValueError, TypeError):
            mail_port = 587

        raw_starttls = (
            settings.MAIL_STARTTLS
            if settings.MAIL_STARTTLS is not None
            else (os.getenv("MAIL_STARTTLS", "true").lower() == "true")
        )
        raw_ssl_tls = (
            settings.MAIL_SSL_TLS
            if settings.MAIL_SSL_TLS is not None
            else (os.getenv("MAIL_SSL_TLS", "false").lower() == "true")
        )

        # Enforce valid TLS protocol per port to prevent mutually exclusive flag conflicts
        if mail_port == 465:
            mail_ssl_tls = True
            mail_starttls = False
        elif mail_port == 587:
            mail_starttls = True
            mail_ssl_tls = False
        else:
            mail_starttls = bool(raw_starttls)
            mail_ssl_tls = bool(raw_ssl_tls)

        has_credentials = bool(mail_username and mail_password)

        self.config = ConnectionConfig(
            MAIL_USERNAME=mail_username,
            MAIL_PASSWORD=mail_password,
            MAIL_FROM=mail_from,
            MAIL_PORT=mail_port,
            MAIL_SERVER=mail_server,
            MAIL_STARTTLS=mail_starttls,
            MAIL_SSL_TLS=mail_ssl_tls,
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
            subject="Reset your YouTube Q&A Assistant password — YtGenius",
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
YtGenius Team
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
            subject="Verify your YouTube Q&A Assistant email — YtGenius",
            recipients=[email],
            body=f"""
Hello,

Welcome to YtGenius.

Please verify your email address by clicking the link below:

{verification_url}

This link will expire soon.

If you did not create this account,
you can safely ignore this email.

Regards,
YtGenius Team
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

    async def send_login_otp_email(
        self,
        email: str,
        otp: str,
        expires_minutes: int | None = None,
    ) -> bool:
        effective_expires = expires_minutes if expires_minutes is not None else getattr(settings, "OTP_EXPIRE_MINUTES", 5)
        message = MessageSchema(
            subject=f"Your YtGenius verification code: {otp}",
            recipients=[email],
            body=f"""Hello,

Your single-use verification code for YtGenius is:

{otp}

This code will expire in {effective_expires} minutes.

If you did not request this login code, you can safely ignore this email.

Regards,
YtGenius Team
""",
            subtype=MessageType.plain,
        )

        if self.fastmail is not None:
            await self.fastmail.send_message(message)
            return True
        else:
            logger.info(
                "SMTP client not configured; skipped delivering login OTP email to %s",
                email,
            )
            return False
