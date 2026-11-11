import os
from pathlib import Path
from typing import List, Optional, Union
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[3]

INSECURE_DEFAULT_SECRET = "ytgenius-insecure-development-secret-key-replace-in-production"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application
    APP_NAME: str = "YtGenius — YouTube Video Q&A Assistant"
    APP_VERSION: str = "2.0.0"
    ENVIRONMENT: str = "development"

    # Database
    DATABASE_URL: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/youtube_qa_db",
        description="PostgreSQL connection string",
    )

    # JWT Authentication
    SECRET_KEY: str = Field(
        default=INSECURE_DEFAULT_SECRET,
        description="JWT signing secret",
    )
    SESSION_SECRET_KEY: Optional[str] = Field(
        default=None,
        description="Dedicated session encryption secret; falls back to SECRET_KEY if unset",
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = 30
    EMAIL_VERIFICATION_TOKEN_EXPIRE_MINUTES: int = 30
    OTP_EXPIRE_MINUTES: int = 5
    OTP_RESEND_COOLDOWN_SECONDS: int = 60
    OTP_MAX_ATTEMPTS: int = 5

    # Database Pool Configuration
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_RECYCLE: int = 1800
    DB_POOL_TIMEOUT: int = 30

    # Rate Limiting & Request Limits
    MAX_REQUEST_BODY_SIZE_BYTES: int = 10 * 1024 * 1024  # 10 MB
    RATE_LIMIT_PER_MINUTE: int = 10
    RATE_LIMIT_BURST: int = 20

    # Reverse Proxy / IP Resolution
    TRUSTED_PROXIES: Union[List[str], str] = ["127.0.0.1", "::1"]

    # Google OAuth
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/auth/google/callback"

    # Frontend URL
    FRONTEND_URL: str = "http://localhost:3000"

    # CORS & Chrome Extension
    CORS_ALLOWED_ORIGINS: Union[List[str], str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]
    CHROME_EXTENSION_IDS: Union[List[str], str] = []

    # Email / SMTP
    MAIL_USERNAME: Optional[str] = None
    MAIL_PASSWORD: Optional[str] = None
    MAIL_FROM: Optional[str] = None
    MAIL_PORT: int = 587
    MAIL_SERVER: str = "smtp.gmail.com"
    MAIL_STARTTLS: bool = True
    MAIL_SSL_TLS: bool = False

    # AI & Vector DB
    GROQ_API_KEY: Optional[str] = None
    GROQ_MODEL: str = "openai/gpt-oss-20b"
    QDRANT_URL: Optional[str] = None
    QDRANT_API_KEY: Optional[str] = None
    QDRANT_COLLECTION: str = "youtube_video_chunks"
    VECTOR_DIMENSION: int = 384
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    RERANKER_MODEL: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    @field_validator("ALGORITHM", mode="before")
    @classmethod
    def validate_jwt_algorithm(cls, value: Optional[str]) -> str:
        if not value:
            return "HS256"
        clean = str(value).strip().upper()
        allowed = {"HS256", "HS384", "HS512"}
        if clean not in allowed:
            raise ValueError(
                f"Insecure or unsupported JWT algorithm '{value}'. "
                f"Allowed secure algorithms are: {', '.join(sorted(allowed))}."
            )
        return clean

    @field_validator("CORS_ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: Union[List[str], str]) -> List[str]:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @field_validator("GOOGLE_REDIRECT_URI", mode="before")
    @classmethod
    def sanitize_google_redirect_uri(cls, value: Optional[str]) -> str:
        if isinstance(value, str):
            clean = value.strip().strip("'\"")
            if clean:
                return clean.rstrip("/")
        return "http://localhost:8000/auth/google/callback"

    @field_validator("CHROME_EXTENSION_IDS", mode="before")
    @classmethod
    def parse_extension_ids(cls, value: Union[List[str], str]) -> List[str]:
        if isinstance(value, str):
            return [ext_id.strip() for ext_id in value.split(",") if ext_id.strip()]
        return value

    @field_validator("TRUSTED_PROXIES", mode="before")
    @classmethod
    def parse_trusted_proxies(cls, value: Union[List[str], str]) -> List[str]:
        if isinstance(value, str):
            return [proxy.strip() for proxy in value.split(",") if proxy.strip()]
        return value

    @model_validator(mode="after")
    def validate_production_security(self) -> "Settings":
        env = (self.ENVIRONMENT or "").strip().lower()
        if env in ("production", "prod"):
            insecure_keys = {
                INSECURE_DEFAULT_SECRET,
                "vidmind-insecure-development-secret-key-replace-in-production",
                "replace-with-a-long-random-secret-key",
                "secret",
                "changeme",
                "admin",
            }
            raw_secret = (self.SECRET_KEY or "").strip()
            if not raw_secret or raw_secret in insecure_keys or len(raw_secret) < 32:
                raise ValueError(
                    "Production security violation: Insecure or default SECRET_KEY is prohibited in production. "
                    "Please set a strong, random SECRET_KEY of at least 32 characters in your environment."
                )

            raw_db = (self.DATABASE_URL or "").strip().lower()
            if (
                not raw_db
                or "localhost" in raw_db
                or "127.0.0.1" in raw_db
                or "postgres:postgres@" in raw_db
            ):
                raise ValueError(
                    "Production security violation: Production requires an explicit, non-localhost DATABASE_URL with non-default credentials."
                )

            raw_frontend = (self.FRONTEND_URL or "").strip()
            raw_frontend_lower = raw_frontend.lower()
            if (
                not raw_frontend
                or "localhost" in raw_frontend_lower
                or "127.0.0.1" in raw_frontend_lower
                or not (raw_frontend_lower.startswith("https://") or raw_frontend_lower.startswith("http://"))
            ):
                raise ValueError(
                    "Production security violation: Production requires an explicit, non-localhost FRONTEND_URL (e.g. https://ytgenius.example.com)."
                )
        return self

    @property
    def all_cors_origins(self) -> List[str]:
        origins = list(self.CORS_ALLOWED_ORIGINS) if isinstance(self.CORS_ALLOWED_ORIGINS, list) else []
        if self.FRONTEND_URL and self.FRONTEND_URL not in origins:
            origins.append(self.FRONTEND_URL.rstrip("/"))
        extension_ids = self.CHROME_EXTENSION_IDS if isinstance(self.CHROME_EXTENSION_IDS, list) else []
        for ext_id in extension_ids:
            ext_origin = f"chrome-extension://{ext_id}"
            if ext_origin not in origins:
                origins.append(ext_origin)
        return origins


settings = Settings()
