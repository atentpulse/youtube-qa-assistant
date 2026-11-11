import hashlib
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock
import pytest
from app.auth.jwt import create_access_token
from app.models.oauth_code import OAuthExchangeCode
from app.models.bug_report import BugReport
from app.models.user import User
from backend.scripts.bootstrap_admin import create_admin, promote_user


@pytest.mark.asyncio
async def test_logout_revokes_token(async_client, db, test_user):
    """Verify that calling /auth/logout immediately revokes existing tokens."""
    token = create_access_token(user_id=test_user.id, token_version=test_user.token_version)
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Valid before logout
    resp = await async_client.get("/auth/me", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == test_user.id

    # 2. Call logout
    logout_resp = await async_client.post("/auth/logout", headers=headers)
    assert logout_resp.status_code == 200
    assert "Successfully logged out" in logout_resp.json()["message"]

    # 3. Invalid after logout
    revoked_resp = await async_client.get("/auth/me", headers=headers)
    assert revoked_resp.status_code == 401
    assert "revoked" in revoked_resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_password_reset_revokes_active_tokens(async_client, db, test_user, auth_service):
    """Verify that completing a password reset invalidates old session tokens."""
    old_token = create_access_token(user_id=test_user.id, token_version=test_user.token_version)
    headers = {"Authorization": f"Bearer {old_token}"}

    # Check valid before reset
    resp = await async_client.get("/auth/me", headers=headers)
    assert resp.status_code == 200

    # Create password reset token and execute reset
    _, raw_reset_token = auth_service.create_password_reset_token(db=db, email=test_user.email)
    auth_service.reset_password(db=db, token=raw_reset_token, new_password="NewSecretPassword123!")

    # Check old token is now rejected
    resp_after = await async_client.get("/auth/me", headers=headers)
    assert resp_after.status_code == 401
    assert "revoked" in resp_after.json()["detail"].lower()


@pytest.mark.asyncio
async def test_oauth_single_use_code_exchange(async_client, db, test_user):
    """Verify single-use authorization code exchange and replay rejection."""
    raw_code = "secure_test_auth_code_xyz123"
    code_hash = hashlib.sha256(raw_code.encode("utf-8")).hexdigest()
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=60)

    oauth_record = OAuthExchangeCode(
        code_hash=code_hash,
        user_id=test_user.id,
        expires_at=expires_at,
        used=False,
    )
    db.add(oauth_record)
    db.commit()

    # 1. First exchange: Success
    exchange_resp = await async_client.post(
        "/auth/oauth/exchange",
        json={"code": raw_code},
    )
    assert exchange_resp.status_code == 200
    data = exchange_resp.json()
    assert "access_token" in data
    assert "refresh_token" in data

    # 2. Verify token works
    user_resp = await async_client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {data['access_token']}"},
    )
    assert user_resp.status_code == 200
    assert user_resp.json()["id"] == test_user.id

    # 3. Second exchange (replay attempt): Rejected
    replay_resp = await async_client.post(
        "/auth/oauth/exchange",
        json={"code": raw_code},
    )
    assert replay_resp.status_code == 400
    assert "already been used" in replay_resp.json()["detail"]


@pytest.mark.asyncio
async def test_oauth_code_expired_rejected(async_client, db, test_user):
    """Verify that expired authorization codes (>60s) cannot be exchanged."""
    raw_code = "expired_test_code_999"
    code_hash = hashlib.sha256(raw_code.encode("utf-8")).hexdigest()
    expired_at = datetime.now(timezone.utc) - timedelta(seconds=10)

    oauth_record = OAuthExchangeCode(
        code_hash=code_hash,
        user_id=test_user.id,
        expires_at=expired_at,
        used=False,
    )
    db.add(oauth_record)
    db.commit()

    res = await async_client.post(
        "/auth/oauth/exchange",
        json={"code": raw_code},
    )
    assert res.status_code == 400
    assert "expired" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_oauth_code_invalid_rejected(async_client):
    """Verify that non-existent or tampered codes return 400."""
    res = await async_client.post(
        "/auth/oauth/exchange",
        json={"code": "completely_fake_and_nonexistent_code"},
    )
    assert res.status_code == 400
    assert "invalid" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_oauth_redirect_never_contains_tokens(async_client, monkeypatch):
    """Verify that Google OAuth redirect URL contains ONLY code and NEVER tokens."""
    from app.routers import auth as auth_router

    fake_user_info = {
        "sub": "google_test_sub_no_leak_456",
        "email": "no_leak_user@example.com",
        "name": "No Leak User",
        "email_verified": True,
    }

    mock_oauth = MagicMock()
    mock_google = MagicMock()
    mock_google.authorize_access_token = AsyncMock(
        return_value={"access_token": "google_raw_access", "userinfo": fake_user_info}
    )
    mock_oauth.google = mock_google
    monkeypatch.setattr(auth_router, "oauth", mock_oauth)

    response = await async_client.get(
        "/auth/google/callback?code=mock_code&state=mock_state",
        follow_redirects=False,
    )
    assert response.status_code == 307
    location = response.headers.get("location", "")
    assert "/oauth/callback" in location
    assert "code=" in location
    assert "token=" not in location
    assert "refresh_token=" not in location


@pytest.mark.asyncio
async def test_admin_role_authorization_for_bug_reports(async_client, db, test_user):
    """Verify that admin bug report triage requires explicit role='admin'."""
    # Seed a bug report
    report = BugReport(
        user_id=test_user.id,
        title="Sample Bug",
        description="A bug description",
        category="bug",
        status="open",
    )
    db.add(report)
    db.commit()

    # 1. Normal user (role='user') -> 403 Forbidden
    normal_token = create_access_token(user_id=test_user.id, token_version=test_user.token_version)
    forbidden_resp = await async_client.get(
        "/api/support/admin/bug-reports",
        headers={"Authorization": f"Bearer {normal_token}"},
    )
    assert forbidden_resp.status_code == 403
    assert "Administrative privileges required" in forbidden_resp.json()["detail"]

    # 2. Promote user to role='admin' -> 200 OK
    test_user.role = "admin"
    db.commit()

    admin_token = create_access_token(user_id=test_user.id, token_version=test_user.token_version)
    admin_resp = await async_client.get(
        "/api/support/admin/bug-reports",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert admin_resp.status_code == 200
    reports = admin_resp.json()
    assert len(reports) >= 1
    assert reports[0]["title"] == "Sample Bug"


def test_admin_bootstrap_functions(db, test_user):
    """Verify safe CLI operational admin bootstrap functions."""
    # Test promote existing user
    assert test_user.role != "admin"
    promoted = promote_user(email=test_user.email, db=db)
    assert promoted is True
    db.refresh(test_user)
    assert test_user.role == "admin"

    # Test create new admin
    created = create_admin(
        email="new_cli_admin@example.com",
        username="SuperAdmin",
        password="SuperAdminSecurePassword123!",
        db=db,
    )
    assert created is True
    new_admin = db.query(User).filter(User.email == "new_cli_admin@example.com").first()
    assert new_admin is not None
    assert new_admin.role == "admin"
    assert new_admin.email_verified is True

    # Duplicate creation rejected
    dup_created = create_admin(
        email="new_cli_admin@example.com",
        username="SuperAdmin",
        password="SuperAdminSecurePassword123!",
        db=db,
    )
    assert dup_created is False


def test_optional_auth_strictly_rejects_refresh_tokens(db, test_user):
    """SEC-06: Verify get_current_user_optional strictly raises 401 when given a refresh token."""
    from fastapi import HTTPException
    from fastapi.security import HTTPAuthorizationCredentials
    from app.auth.jwt import create_refresh_token
    from app.auth.dependencies import get_current_user_optional

    refresh_token = create_refresh_token(user_id=test_user.id)
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=refresh_token)

    with pytest.raises(HTTPException) as exc_info:
        get_current_user_optional(credentials=credentials, db=db)

    assert exc_info.value.status_code == 401
    assert "Refresh token cannot be used for API access" in exc_info.value.detail


def test_rate_limiter_sliding_window_enforcement():
    """SEC-04: Verify thread-safe sliding window rate limiter triggers on burst limit."""
    import os
    from app.core.rate_limiter import RateLimiter

    # Create dedicated limiter with burst of 3
    limiter = RateLimiter(requests_per_minute=3, burst=3)
    # Temporarily remove TESTING flag to test limiter logic
    old_testing = os.environ.get("TESTING")
    try:
        os.environ.pop("TESTING", None)
        assert limiter.is_allowed("192.168.1.100") is True
        assert limiter.is_allowed("192.168.1.100") is True
        assert limiter.is_allowed("192.168.1.100") is True
        # 4th request within window must be rejected
        assert limiter.is_allowed("192.168.1.100") is False
        # Different IP is not blocked
        assert limiter.is_allowed("192.168.1.101") is True
    finally:
        if old_testing is not None:
            os.environ["TESTING"] = old_testing


@pytest.mark.asyncio
async def test_request_body_size_limiter_blocks_large_payload(async_client):
    """SEC-05: Verify requests exceeding max payload size are rejected with 413."""
    from app.core.config import settings
    # Send a request with a Content-Length header greater than MAX_REQUEST_BODY_SIZE_BYTES
    large_length = settings.MAX_REQUEST_BODY_SIZE_BYTES + 1024
    response = await async_client.post(
        "/auth/login",
        headers={"Content-Length": str(large_length), "Content-Type": "application/json"},
        content=b"{}",
    )
    assert response.status_code == 413
    assert "payload too large" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_readiness_probe_does_not_leak_raw_exception(async_client):
    """LOG-01: Verify /health/ready probe returns sanitized messages rather than raw exceptions."""
    from unittest.mock import patch
    from sqlalchemy.exc import OperationalError

    sensitive_leak = "FATAL: password authentication failed for user 'secret_pg_user' on host '10.0.0.5'"
    with patch("sqlalchemy.orm.Session.execute", side_effect=OperationalError(sensitive_leak, {}, Exception())):
        res = await async_client.get("/health/ready")
        assert res.status_code == 503
        data = res.json()
        assert data["status"] == "unhealthy"
        # Must NOT contain the raw database exception or sensitive credentials
        assert sensitive_leak not in data["checks"]["database"]
        assert "secret_pg_user" not in data["checks"]["database"]
        assert "10.0.0.5" not in data["checks"]["database"]
        # Must be cleanly sanitized
        assert data["checks"]["database"] == "unhealthy: database check failed"


def test_rate_limiter_memory_eviction():
    """Verify expired timestamps and stale keys are evicted from memory."""
    import os
    import time
    from app.core.rate_limiter import RateLimiter

    old_testing = os.environ.get("TESTING")
    try:
        os.environ.pop("TESTING", None)
        limiter = RateLimiter(requests_per_minute=5, burst=5, cleanup_interval_seconds=0.01)
        limiter.is_allowed("client-1")
        assert "client-1" in limiter.history

        # Simulate timestamps expiring beyond 60s window
        limiter.history["client-1"] = [time.time() - 70.0]
        # Next is_allowed call triggers cleanup and records new timestamp
        time.sleep(0.02)
        allowed = limiter.is_allowed("client-2")
        assert allowed is True
        # client-1 expired timestamps should have been evicted
        assert "client-1" not in limiter.history
    finally:
        if old_testing is not None:
            os.environ["TESTING"] = old_testing


def test_rate_limiter_capacity_cap():
    """Verify max_keys cap prevents unbounded memory growth."""
    import os
    from app.core.rate_limiter import RateLimiter

    old_testing = os.environ.get("TESTING")
    try:
        os.environ.pop("TESTING", None)
        limiter = RateLimiter(requests_per_minute=10, burst=10, max_keys=5, cleanup_interval_seconds=100.0)
        for i in range(10):
            limiter.is_allowed(f"key-{i}")
        assert len(limiter.history) <= 5
    finally:
        if old_testing is not None:
            os.environ["TESTING"] = old_testing


def test_client_ip_resolution_untrusted_spoofing():
    """Verify untrusted client cannot spoof client IP using X-Forwarded-For."""
    from unittest.mock import MagicMock
    from app.core.rate_limiter import get_client_ip

    mock_request = MagicMock()
    mock_request.client.host = "203.0.113.50"  # Untrusted external IP
    mock_request.headers = {"x-forwarded-for": "1.2.3.4"}

    resolved_ip = get_client_ip(mock_request)
    # Untrusted client's X-Forwarded-For must be ignored
    assert resolved_ip == "203.0.113.50"


def test_client_ip_resolution_trusted_proxy():
    """Verify trusted proxy X-Forwarded-For header is correctly parsed for real client IP."""
    from unittest.mock import MagicMock
    from app.core.rate_limiter import get_client_ip

    mock_request = MagicMock()
    mock_request.client.host = "127.0.0.1"  # Trusted proxy
    mock_request.headers = {"x-forwarded-for": "198.51.100.22, 10.0.0.1"}

    resolved_ip = get_client_ip(mock_request)
    assert resolved_ip == "10.0.0.1"
