import os
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, AsyncMock
from app.models.user import User
from app.models.email_otp import EmailOTP
from app.auth.otp import generate_otp_code, hash_otp_code, verify_otp_code


def test_otp_crypto_utilities():
    """Verify OTP generation and constant-time HMAC hashing."""
    code = generate_otp_code()
    assert len(code) == 6
    assert code.isdigit()

    email = "TestUser@Example.COM"
    h1 = hash_otp_code(email, code)
    h2 = hash_otp_code("testuser@example.com", code)
    # Case-insensitive normalization
    assert h1 == h2
    assert len(h1) == 64  # SHA-256 hex digest

    assert verify_otp_code(email, code, h1) is True
    assert verify_otp_code(email, "000000" if code != "000000" else "111111", h1) is False
    assert verify_otp_code("other@example.com", code, h1) is False


@pytest.mark.asyncio
async def test_send_otp_success_and_secure_storage(async_client, db):
    """Verify POST /auth/otp/send stores only hashed OTP and dispatches email."""
    email = "new_otp_user@example.com"
    with patch("app.services.email_service.EmailService.send_login_otp_email", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = True
        res = await async_client.post("/auth/otp/send", json={"email": email})
        assert res.status_code == 200
        data = res.json()
        assert "6-digit login code has been sent" in data["message"]
        assert data["cooldown_seconds"] == 60

        mock_send.assert_awaited_once()
        sent_args = mock_send.await_args[1]
        raw_otp = sent_args["otp"]
        assert len(raw_otp) == 6
        assert raw_otp.isdigit()

        # Query database to confirm raw OTP is NOT stored plaintext
        otp_record = (
            db.query(EmailOTP)
            .filter(EmailOTP.email == email)
            .order_by(EmailOTP.created_at.desc())
            .first()
        )
        assert otp_record is not None
        assert otp_record.otp_hash != raw_otp
        assert len(otp_record.otp_hash) == 64
        assert otp_record.used_at is None
        assert otp_record.attempts == 0


@pytest.mark.asyncio
async def test_send_otp_resend_cooldown_enforced(async_client, db):
    """Verify resend within 60s cooldown is rejected with HTTP 429."""
    email = "cooldown_test@example.com"
    with patch("app.services.email_service.EmailService.send_login_otp_email", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = True
        # First request succeeds
        r1 = await async_client.post("/auth/otp/send", json={"email": email})
        assert r1.status_code == 200

        # Immediate second request must trigger cooldown
        r2 = await async_client.post("/auth/otp/send", json={"email": email})
        assert r2.status_code == 429
        assert "Please wait" in r2.json()["detail"]


@pytest.mark.asyncio
async def test_send_otp_invalidates_previous_codes(async_client, db):
    """Verify generating a new OTP invalidates previous unused codes for the same email."""
    email = "invalidation_test@example.com"
    with patch("app.services.email_service.EmailService.send_login_otp_email", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = True
        await async_client.post("/auth/otp/send", json={"email": email})
        first_otp = db.query(EmailOTP).filter(EmailOTP.email == email).first()
        first_raw = mock_send.await_args[1]["otp"]

        # Fast forward time beyond cooldown
        first_otp.created_at = datetime.now(timezone.utc) - timedelta(seconds=70)
        db.commit()

        # Request second code
        await async_client.post("/auth/otp/send", json={"email": email})
        second_raw = mock_send.await_args[1]["otp"]

        # First code must now be marked used/invalidated
        db.refresh(first_otp)
        assert first_otp.used_at is not None

        # Verifying with first code must fail
        v1 = await async_client.post("/auth/otp/verify", json={"email": email, "otp": first_raw})
        assert v1.status_code == 400

        # Verifying with second code must succeed
        v2 = await async_client.post("/auth/otp/verify", json={"email": email, "otp": second_raw})
        assert v2.status_code == 200


@pytest.mark.asyncio
async def test_verify_otp_new_user_registration(async_client, db):
    """Verify verifying OTP for nonexistent user creates new verified user and returns JWT."""
    email = "brand_new_user@example.com"
    with patch("app.services.email_service.EmailService.send_login_otp_email", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = True
        await async_client.post("/auth/otp/send", json={"email": email})
        raw_otp = mock_send.await_args[1]["otp"]

    verify_res = await async_client.post("/auth/otp/verify", json={"email": email, "otp": raw_otp})
    assert verify_res.status_code == 200
    data = verify_res.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"

    # Confirm user created in database
    user = db.query(User).filter(User.email == email).first()
    assert user is not None
    assert user.auth_provider == "email_otp"
    assert user.email_verified is True
    assert user.password_hash is None


@pytest.mark.asyncio
async def test_verify_otp_existing_user_login(async_client, db):
    """Verify verifying OTP for existing password user logs them in preserving credentials."""
    email = "existing_user@example.com"
    existing_user = User(
        username="existing_tester",
        email=email,
        password_hash="$2b$12$securepasswordhashplaceholder",
        auth_provider="local",
        email_verified=False,
    )
    db.add(existing_user)
    db.commit()

    with patch("app.services.email_service.EmailService.send_login_otp_email", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = True
        await async_client.post("/auth/otp/send", json={"email": email})
        raw_otp = mock_send.await_args[1]["otp"]

    verify_res = await async_client.post("/auth/otp/verify", json={"email": email, "otp": raw_otp})
    assert verify_res.status_code == 200
    data = verify_res.json()
    assert "access_token" in data

    # Verify user record preserved and now marked verified
    db.refresh(existing_user)
    assert existing_user.email_verified is True
    assert existing_user.password_hash == "$2b$12$securepasswordhashplaceholder"
    assert existing_user.auth_provider == "local"


@pytest.mark.asyncio
async def test_verify_otp_wrong_code_and_max_attempts(async_client, db):
    """Verify incorrect code decrements remaining attempts and locks out after max attempts."""
    email = "attempts_test@example.com"
    with patch("app.services.email_service.EmailService.send_login_otp_email", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = True
        await async_client.post("/auth/otp/send", json={"email": email})
        raw_otp = mock_send.await_args[1]["otp"]

    wrong_code = "999999" if raw_otp != "999999" else "888888"

    # Attempt 1 failed
    r1 = await async_client.post("/auth/otp/verify", json={"email": email, "otp": wrong_code})
    assert r1.status_code == 400
    assert "4 attempt(s) remaining" in r1.json()["detail"]

    # Attempts 2, 3, 4
    for i in range(3, 0, -1):
        res = await async_client.post("/auth/otp/verify", json={"email": email, "otp": wrong_code})
        assert res.status_code == 400

    # Attempt 5: max attempts reached, code burned
    r5 = await async_client.post("/auth/otp/verify", json={"email": email, "otp": wrong_code})
    assert r5.status_code == 400
    assert "Too many incorrect attempts" in r5.json()["detail"]

    # Even right code now fails
    r_late = await async_client.post("/auth/otp/verify", json={"email": email, "otp": raw_otp})
    assert r_late.status_code == 400
    assert "Invalid or expired login code" in r_late.json()["detail"]


@pytest.mark.asyncio
async def test_verify_otp_expired_code(async_client, db):
    """Verify expired OTP code is rejected."""
    email = "expired_test@example.com"
    with patch("app.services.email_service.EmailService.send_login_otp_email", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = True
        await async_client.post("/auth/otp/send", json={"email": email})
        raw_otp = mock_send.await_args[1]["otp"]

    otp_record = db.query(EmailOTP).filter(EmailOTP.email == email).first()
    otp_record.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    db.commit()

    res = await async_client.post("/auth/otp/verify", json={"email": email, "otp": raw_otp})
    assert res.status_code == 400
    assert "expired" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_verify_otp_single_use_replay_prevention(async_client, db):
    """Verify successfully used OTP cannot be replayed."""
    email = "replay_test@example.com"
    with patch("app.services.email_service.EmailService.send_login_otp_email", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = True
        await async_client.post("/auth/otp/send", json={"email": email})
        raw_otp = mock_send.await_args[1]["otp"]

    # First verification succeeds
    res1 = await async_client.post("/auth/otp/verify", json={"email": email, "otp": raw_otp})
    assert res1.status_code == 200

    # Replay attempt must fail
    res2 = await async_client.post("/auth/otp/verify", json={"email": email, "otp": raw_otp})
    assert res2.status_code == 400


@pytest.mark.asyncio
async def test_send_otp_smtp_delivery_failure_returns_503(async_client, db):
    """Verify HTTP 503 is returned when email delivery fails, preventing false success messages."""
    from unittest.mock import PropertyMock
    email = "mail_fail_test@example.com"
    with patch("app.services.email_service.EmailService.is_configured", new_callable=PropertyMock) as mock_cfg:
        mock_cfg.return_value = True
        with patch("app.services.email_service.EmailService.send_login_otp_email", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = False
            with patch.dict(os.environ, {"TESTING": "0"}):
                res = await async_client.post("/auth/otp/send", json={"email": email})
                assert res.status_code == 503
                assert "Failed to send verification code" in res.json()["detail"]


@pytest.mark.asyncio
async def test_send_otp_smtp_not_configured_returns_503(async_client, db):
    """Verify HTTP 503 is returned when SMTP service is unconfigured."""
    from unittest.mock import PropertyMock
    email = "unconfigured_smtp@example.com"
    with patch("app.services.email_service.EmailService.is_configured", new_callable=PropertyMock) as mock_cfg:
        mock_cfg.return_value = False
        with patch.dict(os.environ, {"TESTING": "0"}):
            res = await async_client.post("/auth/otp/send", json={"email": email})
            assert res.status_code == 503
            assert "Email delivery service is not configured" in res.json()["detail"]


@pytest.mark.asyncio
async def test_send_otp_smtp_connection_error_returns_503(async_client, db):
    """Verify HTTP 503 is returned on SMTP connection error without leaking server details."""
    from fastapi_mail.errors import ConnectionErrors
    email = "smtp_conn_err_test@example.com"
    with patch("app.services.email_service.EmailService.send_login_otp_email", new_callable=AsyncMock) as mock_send:
        mock_send.side_effect = ConnectionErrors("Connection refused to mail server")
        res = await async_client.post("/auth/otp/send", json={"email": email})
        assert res.status_code == 503
        assert "Failed to connect to email provider" in res.json()["detail"]


@pytest.mark.asyncio
async def test_global_exception_handler_returns_cors_headers_on_500(async_client):
    """Verify unhandled exceptions return HTTP 500 with proper CORS headers attached."""
    headers = {"Origin": "http://localhost:3000"}
    with patch("app.routers.auth.auth_service.send_login_otp", side_effect=RuntimeError("Simulated unhandled database crash")):
        res = await async_client.post("/auth/otp/send", json={"email": "crash_test@example.com"}, headers=headers)
        assert res.status_code == 500
        assert res.headers.get("access-control-allow-origin") == "http://localhost:3000"
        assert "An internal server error occurred" in res.json()["detail"]
