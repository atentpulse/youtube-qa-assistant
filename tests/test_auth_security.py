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
