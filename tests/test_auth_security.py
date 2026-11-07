import hashlib
from datetime import datetime, timedelta, timezone
import pytest
from app.auth.jwt import create_access_token
from app.models.oauth_code import OAuthExchangeCode
from app.models.bug_report import BugReport
from app.models.user import User


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
