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
    )
    assert s.ENVIRONMENT == "production"
    assert s.SECRET_KEY == strong_secret
