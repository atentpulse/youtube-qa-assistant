import pytest
from pydantic import ValidationError
from app.core.config import Settings, INSECURE_DEFAULT_SECRET


def test_development_allows_default_secret():
    s = Settings(
        ENVIRONMENT="development",
        SECRET_KEY=INSECURE_DEFAULT_SECRET,
    )
    assert s.ENVIRONMENT == "development"
    assert s.SECRET_KEY == INSECURE_DEFAULT_SECRET


def test_production_rejects_default_insecure_secret():
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            ENVIRONMENT="production",
            SECRET_KEY=INSECURE_DEFAULT_SECRET,
        )
    assert "Insecure or default SECRET_KEY is prohibited in production" in str(exc_info.value)


def test_production_rejects_short_secret():
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            ENVIRONMENT="production",
            SECRET_KEY="short-secret-under-32-chars",
        )
    assert "at least 32 characters" in str(exc_info.value)


def test_production_accepts_strong_secret():
    strong_secret = "a" * 32
    s = Settings(
        ENVIRONMENT="production",
        SECRET_KEY=strong_secret,
        DATABASE_URL="postgresql://prod_user:strong_password@prod-db.internal:5432/ytgenius_db",
        FRONTEND_URL="https://ytgenius.example.com",
    )
    assert s.ENVIRONMENT == "production"
    assert s.SECRET_KEY == strong_secret
    assert s.DATABASE_URL == "postgresql://prod_user:strong_password@prod-db.internal:5432/ytgenius_db"
    assert s.FRONTEND_URL == "https://ytgenius.example.com"


def test_production_rejects_localhost_database_url():
    strong_secret = "a" * 32
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            ENVIRONMENT="production",
            SECRET_KEY=strong_secret,
            DATABASE_URL="postgresql://postgres:postgres@localhost:5432/youtube_qa_db",
            FRONTEND_URL="https://ytgenius.example.com",
        )
    assert "Production requires an explicit, non-localhost DATABASE_URL" in str(exc_info.value)


def test_production_rejects_localhost_frontend_url():
    strong_secret = "a" * 32
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            ENVIRONMENT="production",
            SECRET_KEY=strong_secret,
            DATABASE_URL="postgresql://prod_user:pass@prod-db.internal:5432/ytgenius_db",
            FRONTEND_URL="http://localhost:3000",
        )
    assert "Production requires an explicit, non-localhost FRONTEND_URL" in str(exc_info.value)


def test_trusted_proxies_parsing():
    s = Settings(TRUSTED_PROXIES="10.0.0.1, 10.0.0.2 , 192.168.1.1")
    assert s.TRUSTED_PROXIES == ["10.0.0.1", "10.0.0.2", "192.168.1.1"]


def test_production_configuration_fields():
    """Verify new production database pool and session configuration defaults."""
    s = Settings()
    assert s.DB_POOL_SIZE == 10
    assert s.DB_MAX_OVERFLOW == 20
    assert s.DB_POOL_RECYCLE == 1800
    assert s.MAX_REQUEST_BODY_SIZE_BYTES == 10 * 1024 * 1024
    assert s.SESSION_SECRET_KEY is None
    assert s.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES == 30
    assert s.EMAIL_VERIFICATION_TOKEN_EXPIRE_MINUTES == 30
    assert s.OTP_EXPIRE_MINUTES == 5
    assert s.OTP_RESEND_COOLDOWN_SECONDS == 60
    assert s.OTP_MAX_ATTEMPTS == 5
    assert s.VECTOR_DIMENSION == 384
    assert s.EMBEDDING_MODEL == "all-MiniLM-L6-v2"
    assert s.RERANKER_MODEL == "cross-encoder/ms-marco-MiniLM-L-6-v2"
    assert s.QDRANT_COLLECTION == "youtube_video_chunks"
    assert s.ALGORITHM == "HS256"


def test_jwt_algorithm_allowed():
    for algo in ["HS256", "HS384", "hs512"]:
        s = Settings(ALGORITHM=algo)
        assert s.ALGORITHM == algo.upper()


def test_jwt_algorithm_rejects_unsafe_none():
    with pytest.raises(ValidationError) as exc:
        Settings(ALGORITHM="none")
    assert "Insecure or unsupported JWT algorithm" in str(exc.value)


def test_jwt_algorithm_rejects_unknown():
    with pytest.raises(ValidationError) as exc:
        Settings(ALGORITHM="RS256")
    assert "Insecure or unsupported JWT algorithm" in str(exc.value)
