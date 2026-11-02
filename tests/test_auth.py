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
