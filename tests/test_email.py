import logging
import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi_mail.errors import ConnectionErrors
from app.services.email_service import EmailService
from app.core.config import settings


@pytest.mark.asyncio
async def test_email_unconfigured_delivery_does_not_crash(caplog):
    service = EmailService()
    service.fastmail = None
    assert service.is_configured is False

    with caplog.at_level(logging.INFO):
        # 1. Password reset
        secret_reset_url = "https://app.ytgenius.com/reset?token=super-secret-token-12345"
        res_reset = await service.send_password_reset_email(
            email="user@example.com",
            reset_url=secret_reset_url,
        )
        assert res_reset is False

        # Verify token is NOT logged in caplog
        assert "super-secret-token-12345" not in caplog.text
        assert "user@example.com" in caplog.text

        # 2. Email verification
        secret_verify_url = "https://app.ytgenius.com/verify?token=super-secret-verify-67890"
        res_verify = await service.send_email_verification(
            email="user2@example.com",
            verification_url=secret_verify_url,
        )
        assert res_verify is False
        assert "super-secret-verify-67890" not in caplog.text
        assert "user2@example.com" in caplog.text


@pytest.mark.asyncio
async def test_email_configured_delivery():
    service = EmailService()
    mock_fastmail = MagicMock()
    mock_fastmail.send_message = AsyncMock(return_value=None)
    service.fastmail = mock_fastmail
    assert service.is_configured is True

    # 1. Password reset
    res_reset = await service.send_password_reset_email(
        email="user@example.com",
        reset_url="https://app.ytgenius.com/reset?token=abc",
    )
    assert res_reset is True
    assert mock_fastmail.send_message.call_count == 1
    call_args = mock_fastmail.send_message.call_args[0][0]
    recipient_email = getattr(call_args.recipients[0], "email", str(call_args.recipients[0]))
    assert recipient_email == "user@example.com"
    assert "Reset your YouTube Q&A Assistant password" in call_args.subject

    # 2. Email verification
    res_verify = await service.send_email_verification(
        email="user@example.com",
        verification_url="https://app.ytgenius.com/verify?token=xyz",
    )
    assert res_verify is True
    assert mock_fastmail.send_message.call_count == 2


def test_email_password_whitespace_sanitization(monkeypatch):
    monkeypatch.setattr(settings, "MAIL_USERNAME", "sender@example.com")
    monkeypatch.setattr(settings, "MAIL_PASSWORD", "  abcd efgh ijkl mnop  ")
    monkeypatch.setattr(settings, "MAIL_PORT", 587)
    monkeypatch.setenv("MAIL_USERNAME", "sender@example.com")
    monkeypatch.setenv("MAIL_PASSWORD", "  abcd efgh ijkl mnop  ")
    monkeypatch.setenv("MAIL_PORT", "587")

    service = EmailService()
    raw_pw = service.config.MAIL_PASSWORD
    actual_pw = raw_pw.get_secret_value() if hasattr(raw_pw, "get_secret_value") else raw_pw
    assert actual_pw == "abcdefghijklmnop"
    assert service.config.MAIL_USERNAME == "sender@example.com"


def test_email_tls_protocol_by_port(monkeypatch):
    monkeypatch.setattr(settings, "MAIL_USERNAME", "sender@example.com")
    monkeypatch.setattr(settings, "MAIL_PASSWORD", "secretpassword123")
    monkeypatch.setenv("MAIL_USERNAME", "sender@example.com")
    monkeypatch.setenv("MAIL_PASSWORD", "secretpassword123")

    # Test port 465 forces SSL_TLS=True, STARTTLS=False
    monkeypatch.setattr(settings, "MAIL_PORT", 465)
    monkeypatch.setattr(settings, "MAIL_STARTTLS", True)
    monkeypatch.setattr(settings, "MAIL_SSL_TLS", False)
    monkeypatch.setenv("MAIL_PORT", "465")
    monkeypatch.setenv("MAIL_STARTTLS", "True")  # Misconfigured env should be corrected
    monkeypatch.setenv("MAIL_SSL_TLS", "False")
    service_465 = EmailService()
    assert service_465.config.MAIL_PORT == 465
    assert service_465.config.MAIL_SSL_TLS is True
    assert service_465.config.MAIL_STARTTLS is False

    # Test port 587 forces STARTTLS=True, SSL_TLS=False
    monkeypatch.setattr(settings, "MAIL_PORT", 587)
    monkeypatch.setattr(settings, "MAIL_STARTTLS", False)
    monkeypatch.setattr(settings, "MAIL_SSL_TLS", True)
    monkeypatch.setenv("MAIL_PORT", "587")
    monkeypatch.setenv("MAIL_STARTTLS", "False")  # Misconfigured env should be corrected
    monkeypatch.setenv("MAIL_SSL_TLS", "True")
    service_587 = EmailService()
    assert service_587.config.MAIL_PORT == 587
    assert service_587.config.MAIL_STARTTLS is True
    assert service_587.config.MAIL_SSL_TLS is False


@pytest.mark.asyncio
async def test_email_exception_propagates():
    service = EmailService()
    mock_fastmail = MagicMock()
    mock_fastmail.send_message = AsyncMock(side_effect=ConnectionErrors("Connection EOF"))
    service.fastmail = mock_fastmail

    with pytest.raises(ConnectionErrors):
        await service.send_email_verification("user@example.com", "https://app.ytgenius.com/verify?token=xyz")
