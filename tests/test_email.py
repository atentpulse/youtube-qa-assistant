import logging
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.email_service import EmailService


@pytest.mark.asyncio
async def test_email_unconfigured_delivery_does_not_crash(caplog):
    service = EmailService()
    service.fastmail = None
    assert service.is_configured is False

    with caplog.at_level(logging.INFO):
        # 1. Password reset
        secret_reset_url = "https://app.vidmind.ai/reset?token=super-secret-token-12345"
        res_reset = await service.send_password_reset_email(
            email="user@example.com",
            reset_url=secret_reset_url,
        )
        assert res_reset is False

        # Verify token is NOT logged in caplog
        assert "super-secret-token-12345" not in caplog.text
        assert "user@example.com" in caplog.text

        # 2. Email verification
        secret_verify_url = "https://app.vidmind.ai/verify?token=super-secret-verify-67890"
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
        reset_url="https://app.vidmind.ai/reset?token=abc",
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
        verification_url="https://app.vidmind.ai/verify?token=xyz",
    )
    assert res_verify is True
    assert mock_fastmail.send_message.call_count == 2
