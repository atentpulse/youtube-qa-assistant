import os
import sys
from unittest.mock import AsyncMock, MagicMock

os.environ["TESTING"] = "1"
os.environ["QDRANT_URL"] = ":memory:"
os.environ["SECRET_KEY"] = "test-secret-key-for-unit-testing-32-chars-long"

# 1. Mock sentence_transformers and heavy ML models for fast headless testing
mock_st = MagicMock()
mock_model = MagicMock()
mock_model.encode.return_value = [0.1] * 384
mock_model.get_sentence_embedding_dimension.return_value = 384
mock_st.SentenceTransformer.return_value = mock_model
sys.modules["sentence_transformers"] = mock_st
sys.modules["sentence_transformers.cross_encoder"] = MagicMock()

import pytest
import pytest_asyncio
import httpx
from starlette.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.database import Base, get_db
from app.auth.jwt import create_access_token
from app.models import (
    User,
    Video,
    UserVideo,
    Conversation,
    Message,
    QuestionCache,
    PasswordResetToken,
    EmailVerificationToken,
    BugReport,
    OAuthExchangeCode,
)
from app.services.auth_service import AuthService
from app.services.email_service import EmailService
from app.services.video_storage_service import VideoStorageService
from app.dependencies import get_rag_service
from app.main import app
import app.routers.auth as auth_router


# In-memory SQLite engine
engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def setup_database():
    """Create all tables before each test and drop them after."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def mock_external_network(monkeypatch):
    """Ensure email service does not attempt live SMTP connections during router tests."""
    monkeypatch.setattr(
        auth_router.email_service,
        "send_email_verification",
        AsyncMock(return_value=True),
    )
    monkeypatch.setattr(
        auth_router.email_service,
        "send_password_reset_email",
        AsyncMock(return_value=True),
    )
    # Ensure RAG background tasks use the test SQLite DB instead of PostgreSQL
    import app.services.rag_service as rag_service_mod
    monkeypatch.setattr(rag_service_mod, "SessionLocal", TestingSessionLocal)

    # Configure dummy delete_video on app.state.rag_service
    def dummy_delete_video(db, user_id, video_id):
        storage = VideoStorageService(db)
        return storage.delete_video(video_id=video_id, user_id=user_id)

    if not hasattr(app.state, "rag_service") or app.state.rag_service is None:
        from unittest.mock import MagicMock
        app.state.rag_service = MagicMock()
    app.state.rag_service.delete_video.side_effect = dummy_delete_video


@pytest.fixture
def db():
    """Provide a clean database session for each test."""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def override_get_db(db):
    """Override FastAPI get_db dependency to use test SQLite DB."""
    def _get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = _get_db
    yield
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def mock_rag_service():
    """Provide a mock RAG service for deterministic API testing."""
    mock = MagicMock()
    mock._in_flight_videos = set()

    def dummy_ask(db, user_id, video_id, question, conversation_context="", rewrite_context="", top_k=15):
        return {
            "question": question,
            "answer": f"Answer about {video_id}: {question}",
            "sources": [
                {
                    "start_time": 10.0,
                    "end_time": 25.0,
                    "start_time_formatted": "00:10",
                    "end_time_formatted": "00:25",
                    "url": f"https://www.youtube.com/watch?v={video_id}&t=10s",
                    "score": 0.95,
                }
            ],
            "cached": False,
        }

    def dummy_get_all_videos(db, user_id, limit=10, offset=0, status=None):
        storage = VideoStorageService(db)
        videos = storage.get_all_videos(user_id=user_id, limit=limit, offset=offset, status=status)
        total = storage.get_video_count(user_id=user_id, status=status)
        return {"videos": videos, "total": total}

    def dummy_delete_video(db, user_id, video_id):
        storage = VideoStorageService(db)
        return storage.delete_video(video_id=video_id, user_id=user_id)

    mock.ask_question.side_effect = dummy_ask
    mock.get_all_videos.side_effect = dummy_get_all_videos
    mock.delete_video.side_effect = dummy_delete_video
    return mock


@pytest.fixture
def override_rag_service(mock_rag_service):
    """Override FastAPI get_rag_service dependency."""
    app.dependency_overrides[get_rag_service] = lambda: mock_rag_service
    yield mock_rag_service
    app.dependency_overrides.pop(get_rag_service, None)


@pytest.fixture
def auth_service():
    return AuthService()


@pytest.fixture
def test_user(db, auth_service):
    """Create and return a verified test user."""
    user = auth_service.register_user(
        db=db,
        username="testuser",
        email="testuser@example.com",
        password="TestPassword123!",
    )
    user.email_verified = True
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def test_user_2(db, auth_service):
    """Create and return a second verified test user."""
    user = auth_service.register_user(
        db=db,
        username="otheruser",
        email="otheruser@example.com",
        password="OtherPassword123!",
    )
    user.email_verified = True
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def user_token(test_user):
    """Return JWT token for test_user."""
    return create_access_token(test_user.id)


@pytest.fixture
def user_2_token(test_user_2):
    """Return JWT token for test_user_2."""
    return create_access_token(test_user_2.id)


@pytest.fixture
def auth_headers(user_token):
    return {"Authorization": f"Bearer {user_token}"}


@pytest.fixture
def auth_headers_2(user_2_token):
    return {"Authorization": f"Bearer {user_2_token}"}


@pytest.fixture
def client():
    """Synchronous test client for CORS and middleware testing."""
    return TestClient(app)


@pytest_asyncio.fixture
async def async_client(override_get_db, override_rag_service):
    """Async ASGI client using httpx transport without loopback TCP."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
