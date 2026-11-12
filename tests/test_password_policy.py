import pytest
from httpx import ASGITransport, AsyncClient
import bcrypt

from app.auth.password import hash_password, verify_password, MAX_BCRYPT_BYTES
from app.models.user import User
from app.services.auth_service import AuthService
from app.main import app


# ---------------------------------------------------------------------------
# 1. New password below 72 bytes
# ---------------------------------------------------------------------------
def test_new_password_below_72_bytes():
    password = "ValidSecurePassword123!"
    assert len(password.encode("utf-8")) < 72
    hashed = hash_password(password)
    assert hashed.startswith("$2b$12$")
    assert verify_password(password, hashed) is True
    assert verify_password("WrongPassword123!", hashed) is False


# ---------------------------------------------------------------------------
# 2. New password exactly 72 bytes
# ---------------------------------------------------------------------------
def test_new_password_exactly_72_bytes():
    password = "A" * 72
    assert len(password.encode("utf-8")) == 72
    hashed = hash_password(password)
    assert hashed.startswith("$2b$12$")
    assert verify_password(password, hashed) is True
    assert verify_password("A" * 71 + "B", hashed) is False


# ---------------------------------------------------------------------------
# 3. New password above 72 bytes
# ---------------------------------------------------------------------------
def test_new_password_above_72_bytes():
    # 73 ASCII bytes
    password_73 = "A" * 73
    assert len(password_73.encode("utf-8")) == 73
    with pytest.raises(ValueError) as exc_info:
        hash_password(password_73)
    assert "exceeds maximum allowed length" in str(exc_info.value) or "72 bytes" in str(exc_info.value)

    # 85 ASCII bytes
    password_85 = "B" * 85
    assert len(password_85.encode("utf-8")) == 85
    with pytest.raises(ValueError) as exc_info:
        hash_password(password_85)
    assert "72 bytes" in str(exc_info.value)


# ---------------------------------------------------------------------------
# 4. Multibyte input crossing the 72-byte boundary
# ---------------------------------------------------------------------------
def test_multibyte_input_crossing_72_byte_boundary():
    # 20 CJK chars * 3 bytes/char = 60 bytes (<= 72 bytes, valid)
    valid_cjk = "こんにちは世界テストパスワードです！"
    assert len(valid_cjk.encode("utf-8")) == 54  # 18 chars * 3 bytes = 54 bytes
    h_cjk = hash_password(valid_cjk)
    assert verify_password(valid_cjk, h_cjk) is True

    # 29 CJK chars = 87 bytes (> 72 bytes, invalid)
    long_cjk = "こんにちは世界テストパスワードです！長い追加テキスト"
    assert len(long_cjk.encode("utf-8")) == 78  # 26 chars * 3 bytes = 78 bytes > 72
    with pytest.raises(ValueError) as exc_info:
        hash_password(long_cjk)
    assert "72 bytes" in str(exc_info.value)

    # 71 ASCII chars + 1 3-byte unicode char = 74 bytes (character count 72, byte count 74)
    split_multibyte = "x" * 71 + "€"
    assert len(split_multibyte) == 72
    assert len(split_multibyte.encode("utf-8")) == 74
    with pytest.raises(ValueError) as exc_info:
        hash_password(split_multibyte)
    assert "72 bytes" in str(exc_info.value)

    # 70 ASCII chars + 1 2-byte unicode char = 72 bytes (character count 71, byte count 72)
    boundary_multibyte = "x" * 70 + "é"
    assert len(boundary_multibyte) == 71
    assert len(boundary_multibyte.encode("utf-8")) == 72
    h_boundary = hash_password(boundary_multibyte)
    assert verify_password(boundary_multibyte, h_boundary) is True


# ---------------------------------------------------------------------------
# 5. Legacy hash verification for passwords longer than 72 bytes
# ---------------------------------------------------------------------------
def test_legacy_hash_verification_for_passwords_longer_than_72_bytes():
    # Passlib historically hashed passwords > 72 bytes by silently truncating to 72 bytes
    long_password = "LegacySecretPassword123!" + "X" * 60  # ~84 bytes
    assert len(long_password.encode("utf-8")) > 72

    # Simulate Passlib hash generation by hashing the first 72 bytes
    truncated_bytes = long_password.encode("utf-8")[:MAX_BCRYPT_BYTES]
    salt = bcrypt.gensalt()
    legacy_hash = bcrypt.hashpw(truncated_bytes, salt).decode("utf-8")

    # verify_password must accept the full original untruncated password
    assert verify_password(long_password, legacy_hash) is True
    # verify_password must also accept the exactly truncated 72 bytes
    assert verify_password(long_password[:MAX_BCRYPT_BYTES], legacy_hash) is True
    # verify_password must reject mismatched prefix
    assert verify_password("WrongPrefix" + "X" * 60, legacy_hash) is False


# ---------------------------------------------------------------------------
# 6. Existing $2a$ and $2b$ hash verification
# ---------------------------------------------------------------------------
def test_existing_2a_and_2b_hash_verification():
    # Real $2a$ hash generated with bcrypt 2a identifier for "hello123"
    hash_2a = "$2a$12$qUjB3K55D5VKM/ZBk62VUOlg4EJdipJTdn04uVwv59srG5BiQZc2."
    assert verify_password("hello123", hash_2a) is True
    assert verify_password("wrongpassword", hash_2a) is False

    # Real $2b$ hash generated with bcrypt 2b identifier for "hello123"
    hash_2b = "$2b$12$KRFuKfxa2NAng9PgZdkLGORK7mlMiVhrbVUPAJq1k.k.NMvJepdom"
    assert verify_password("hello123", hash_2b) is True
    assert verify_password("wrongpassword", hash_2b) is False


# ---------------------------------------------------------------------------
# 7. Registration and password-reset validation
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_registration_and_password_reset_validation(async_client, db):
    # 7.1 Registration with valid 72-byte password succeeds schema validation
    resp_valid = await async_client.post(
        "/auth/register",
        json={
            "email": "pwd_test_valid@example.com",
            "username": "pwd_test_valid",
            "password": "V" * 72,
        },
    )
    assert resp_valid.status_code in (200, 201)

    # 7.2 Registration with 73-byte password is rejected with 422
    resp_invalid_73 = await async_client.post(
        "/auth/register",
        json={
            "email": "pwd_test_invalid@example.com",
            "username": "pwd_test_invalid",
            "password": "I" * 73,
        },
    )
    assert resp_invalid_73.status_code == 422
    errors = resp_invalid_73.json().get("detail", [])
    assert any("72 bytes" in str(err) for err in errors)

    # 7.3 Registration with multibyte password crossing 72 bytes is rejected
    resp_invalid_multi = await async_client.post(
        "/auth/register",
        json={
            "email": "pwd_test_multi@example.com",
            "username": "pwd_test_multi",
            "password": "M" * 71 + "€",  # 74 UTF-8 bytes
        },
    )
    assert resp_invalid_multi.status_code == 422
    errors = resp_invalid_multi.json().get("detail", [])
    assert any("72 bytes" in str(err) for err in errors)

    # 7.4 Password reset validation: invalid token with > 72 bytes new_password is rejected at schema level (422)
    resp_reset_invalid = await async_client.post(
        "/auth/reset-password",
        json={
            "token": "any_token",
            "new_password": "R" * 73,
        },
    )
    assert resp_reset_invalid.status_code == 422
    errors = resp_reset_invalid.json().get("detail", [])
    assert any("72 bytes" in str(err) for err in errors)


# ---------------------------------------------------------------------------
# 8. Existing login behavior for legacy accounts
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_existing_login_behavior_for_legacy_accounts(async_client, db):
    auth_srv = AuthService()
    legacy_email = "legacy_user@example.com"
    legacy_long_password = "LegacyUserSecret123!" + "L" * 60  # 80 bytes
    assert len(legacy_long_password.encode("utf-8")) == 80

    # Simulate an existing account created under legacy Passlib
    # Legacy Passlib stored hash of the first 72 bytes
    truncated_bytes = legacy_long_password.encode("utf-8")[:MAX_BCRYPT_BYTES]
    salt = bcrypt.gensalt()
    legacy_hash = bcrypt.hashpw(truncated_bytes, salt).decode("utf-8")

    user = User(
        username="legacy_user",
        email=legacy_email,
        password_hash=legacy_hash,
        auth_provider="local",
        email_verified=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # The user logs in sending their full 80-byte password
    login_resp = await async_client.post(
        "/auth/login",
        json={
            "email": legacy_email,
            "password": legacy_long_password,
        },
    )
    assert login_resp.status_code == 200
    data = login_resp.json()
    assert "access_token" in data
    assert "refresh_token" in data

    # Verify that wrong password is still rejected
    wrong_login = await async_client.post(
        "/auth/login",
        json={
            "email": legacy_email,
            "password": "WrongPassword123!",
        },
    )
    assert wrong_login.status_code == 401
