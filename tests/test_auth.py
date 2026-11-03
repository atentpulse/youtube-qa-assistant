from datetime import timedelta
import pytest
from app.auth.jwt import create_access_token, create_refresh_token


@pytest.mark.asyncio
async def test_register_success(async_client):
    response = await async_client.post(
        "/auth/register",
        json={
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "Password123!",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "newuser@example.com"
    assert data["username"] == "newuser"
    assert "id" in data


@pytest.mark.asyncio
async def test_register_duplicate_email(async_client, test_user):
    response = await async_client.post(
        "/auth/register",
        json={
            "username": "duplicate",
            "email": test_user.email,
            "password": "Password123!",
        },
    )
    assert response.status_code == 400
    assert "already registered" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_login_success(async_client, test_user):
    response = await async_client.post(
        "/auth/login",
        json={
            "email": test_user.email,
            "password": "TestPassword123!",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_invalid_password(async_client, test_user):
    response = await async_client.post(
        "/auth/login",
        json={
            "email": test_user.email,
            "password": "WrongPassword123!",
        },
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_me(async_client, test_user, auth_headers):
    response = await async_client.get("/auth/me", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == test_user.email
    assert data["username"] == test_user.username


@pytest.mark.asyncio
async def test_get_users_me_alias(async_client, test_user, auth_headers):
    response = await async_client.get("/users/me", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == test_user.email
    assert data["id"] == test_user.id


@pytest.mark.asyncio
async def test_refresh_token_active_bearer_header(async_client, auth_headers):
    # Existing frontend contract: POST /auth/refresh with Bearer header
    response = await async_client.post("/auth/refresh", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"

    # Verify that the new access token is valid for authenticated routes
    new_headers = {"Authorization": f"Bearer {data['access_token']}"}
    me_response = await async_client.get("/auth/me", headers=new_headers)
    assert me_response.status_code == 200


@pytest.mark.asyncio
async def test_refresh_token_dedicated_body(async_client, test_user):
    # Standard refresh lifecycle: POST /auth/refresh with refresh_token in body
    refresh_tok = create_refresh_token(test_user.id)
    response = await async_client.post(
        "/auth/refresh",
        json={"refresh_token": refresh_tok},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data

    # Verify rotated refresh token can also be used
    rotated_refresh = data["refresh_token"]
    resp2 = await async_client.post(
        "/auth/refresh",
        json={"refresh_token": rotated_refresh},
    )
    assert resp2.status_code == 200


@pytest.mark.asyncio
async def test_refresh_token_expired_bearer_rejected(async_client, test_user):
    # Expired access token in header must be strictly rejected
    expired_token = create_access_token(
        test_user.id,
        expires_delta=timedelta(seconds=-10),
    )
    response = await async_client.post(
        "/auth/refresh",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert response.status_code == 401
    assert "expired" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_refresh_token_expired_body_rejected(async_client, test_user):
    # Expired refresh token in body must be strictly rejected
    expired_refresh = create_refresh_token(
        test_user.id,
        expires_delta=timedelta(seconds=-10),
    )
    response = await async_client.post(
        "/auth/refresh",
        json={"refresh_token": expired_refresh},
    )
    assert response.status_code == 401
    assert "expired" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_refresh_token_invalid_signature_rejected(async_client):
    response = await async_client.post(
        "/auth/refresh",
        json={"refresh_token": "tampered.jwt.token"},
    )
    assert response.status_code == 401
    assert "invalid" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_refresh_token_access_token_rejected_in_body(async_client, test_user):
    # Passing an access token where a refresh token is expected must be rejected
    acc_tok = create_access_token(test_user.id)
    response = await async_client.post(
        "/auth/refresh",
        json={"refresh_token": acc_tok},
    )
    assert response.status_code == 401
    assert "not a valid refresh token" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_api_access_with_refresh_token_rejected(async_client, test_user):
    # Passing a refresh token to a protected API route (like /auth/me) must be rejected
    ref_tok = create_refresh_token(test_user.id)
    response = await async_client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {ref_tok}"},
    )
    assert response.status_code == 401
    assert "refresh token cannot be used for api access" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_forgot_and_reset_password(async_client, db, test_user):
    fp_response = await async_client.post(
        "/auth/forgot-password",
        json={"email": test_user.email},
    )
    assert fp_response.status_code == 200
    assert "message" in fp_response.json()

    from app.services.auth_service import AuthService
    auth_srv = AuthService()
    user, raw_token = auth_srv.create_password_reset_token(db, test_user.email)
    assert raw_token is not None

    reset_response = await async_client.post(
        "/auth/reset-password",
        json={
            "token": raw_token,
            "new_password": "NewSecretPassword123!",
        },
    )
    assert reset_response.status_code == 200

    login_response = await async_client.post(
        "/auth/login",
        json={
            "email": test_user.email,
            "password": "NewSecretPassword123!",
        },
    )
    assert login_response.status_code == 200

@pytest.mark.asyncio
async def test_register_smtp_failure_returns_503_and_allows_retry(async_client, db, monkeypatch):
    import app.routers.auth as auth_router
    from unittest.mock import AsyncMock
    from fastapi_mail.errors import ConnectionErrors
    from app.models.user import User

    # 1. Simulate SMTP connection drop during verification email sending
    monkeypatch.setattr(
        auth_router.email_service,
        "send_email_verification",
        AsyncMock(side_effect=ConnectionErrors("Unexpected EOF received")),
    )

    reg_payload = {
        "username": "unverifieduser",
        "email": "unverified@example.com",
        "password": "Password123!",
    }
    response = await async_client.post("/auth/register", json=reg_payload)
    assert response.status_code == 503
    assert "verification email could not be sent" in response.json()["detail"].lower()

    # 2. Check user was persisted in DB with email_verified=False
    user = db.query(User).filter(User.email == "unverified@example.com").first()
    assert user is not None
    assert user.email_verified is False

    # 3. User can retry registration (with updated username/password)
    # Restore working email service
    monkeypatch.setattr(
        auth_router.email_service,
        "send_email_verification",
        AsyncMock(return_value=True),
    )

    retry_payload = {
        "username": "unverifieduser_updated",
        "email": "unverified@example.com",
        "password": "NewPassword456!",
    }
    retry_resp = await async_client.post("/auth/register", json=retry_payload)
    assert retry_resp.status_code == 200
    assert retry_resp.json()["username"] == "unverifieduser_updated"

    # 4. Once verified, registration attempt MUST fail with 400
    user.email_verified = True
    db.commit()

    dup_resp = await async_client.post("/auth/register", json=retry_payload)
    assert dup_resp.status_code == 400
    assert "already registered" in dup_resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_resend_verification_smtp_failure_returns_503(async_client, db, monkeypatch):
    import app.routers.auth as auth_router
    from unittest.mock import AsyncMock
    from fastapi_mail.errors import ConnectionErrors
    from app.models.user import User

    # Create unverified user
    unverified_user = User(
        username="resenduser",
        email="resenduser@example.com",
        password_hash="fakehash",
        email_verified=False,
    )
    db.add(unverified_user)
    db.commit()

    monkeypatch.setattr(
        auth_router.email_service,
        "send_email_verification",
        AsyncMock(side_effect=ConnectionErrors("Connection timed out")),
    )

    response = await async_client.post(
        "/auth/resend-verification",
        json={"email": "resenduser@example.com"},
    )
    assert response.status_code == 503
    assert "verification email could not be sent" in response.json()["detail"].lower()

@pytest.mark.asyncio
async def test_real_registration_to_verification_flow(async_client, db, monkeypatch):
    import urllib.parse
    import hashlib
    from unittest.mock import AsyncMock
    import app.routers.auth as auth_router
    from app.models.user import User
    from app.models.email_verification_token import EmailVerificationToken

    # 1. Capture the exact email and verification_url sent to the email service
    captured_calls = []

    async def mock_send(email, verification_url):
        captured_calls.append({"email": email, "url": verification_url})
        return True

    monkeypatch.setattr(auth_router.email_service, "send_email_verification", mock_send)

    # 2. Register user
    reg_email = "dynamic_user@example.com"
    reg_password = "SecurePassword123!"
    reg_response = await async_client.post(
        "/auth/register",
        json={
            "username": "dynamicuser",
            "email": reg_email,
            "password": reg_password,
        },
    )
    assert reg_response.status_code == 200
    reg_data = reg_response.json()
    assert reg_data["email"] == reg_email
    assert reg_data["email_verified"] is False

    # 3. Verify email service received the real unique token
    assert len(captured_calls) == 1
    call = captured_calls[0]
    assert call["email"] == reg_email

    parsed_url = urllib.parse.urlparse(call["url"])
    assert parsed_url.path == "/verify-email"
    query_params = urllib.parse.parse_qs(parsed_url.query)
    assert "token" in query_params
    actual_token = query_params["token"][0]

    # Verify token is dynamically generated, cryptographically strong, and NOT a hardcoded test token
    assert actual_token != "test_token_123"
    assert len(actual_token) >= 40

    # 4. Verify token hash was stored in database
    expected_hash = hashlib.sha256(actual_token.encode("utf-8")).hexdigest()
    token_record = (
        db.query(EmailVerificationToken)
        .filter(EmailVerificationToken.token_hash == expected_hash)
        .first()
    )
    assert token_record is not None
    assert token_record.user_id == reg_data["id"]
    assert token_record.used_at is None

    # 5. Attempt login before email verification -> MUST FAIL with 401
    login_before = await async_client.post(
        "/auth/login",
        json={"email": reg_email, "password": reg_password},
    )
    assert login_before.status_code == 401
    assert "verify your email" in login_before.json()["detail"].lower()

    # 6. Attempt verification with a hardcoded test token -> MUST FAIL with 400
    fake_verify = await async_client.get("/auth/verify-email?token=test_token_123")
    assert fake_verify.status_code == 400
    assert "invalid or expired" in fake_verify.json()["detail"].lower()

    # 7. Verify using the actual dynamically generated token -> MUST SUCCEED with 200
    real_verify = await async_client.get(f"/auth/verify-email?token={actual_token}")
    assert real_verify.status_code == 200
    assert "verified successfully" in real_verify.json()["message"].lower()

    # 8. Check database state
    db.refresh(token_record)
    assert token_record.used_at is not None
    user_in_db = db.query(User).filter(User.id == reg_data["id"]).first()
    assert user_in_db.email_verified is True

    # 9. Attempt verification again with the same token -> MUST FAIL with 400
    reuse_verify = await async_client.get(f"/auth/verify-email?token={actual_token}")
    assert reuse_verify.status_code == 400
    assert "already been used" in reuse_verify.json()["detail"].lower()

    # 10. Attempt login after verification -> MUST SUCCEED with 200
    login_after = await async_client.post(
        "/auth/login",
        json={"email": reg_email, "password": reg_password},
    )
    assert login_after.status_code == 200
    login_data = login_after.json()
    assert "access_token" in login_data
    assert "refresh_token" in login_data

