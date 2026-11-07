import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.core import settings
from app.database.database import engine, get_db
from app.services.qdrant_service import QdrantVectorStore
from app.models import (
    User,
    Conversation,
    Message,
    Video,
    UserVideo,
    QuestionCache,
    PasswordResetToken,
    EmailVerificationToken,
    BugReport,
)
from app.routers import (
    auth,
    conversations,
    videos,
    questions,
    support,
)
from app.schemas.auth import UserResponse
from app.services.rag_service import RAGService


@asynccontextmanager
async def lifespan(app: FastAPI):
    if os.getenv('TESTING') == '1':
        from unittest.mock import MagicMock
        app.state.rag_service = MagicMock()
    else:
        app.state.rag_service = RAGService()
        try:
            from app.database.database import SessionLocal
            from app.services.video_storage_service import VideoStorageService
            import logging
            with SessionLocal() as db:
                recovered = VideoStorageService(db).recover_stale_jobs(max_age_minutes=15)
                if recovered:
                    logging.getLogger(__name__).info(
                        "Recovered %d stale video jobs on startup: %s",
                        len(recovered),
                        recovered,
                    )
        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning(
                "Startup stale job recovery failed: %s",
                exc,
            )
    yield


# --------------------------------
# Create FastAPI app
# --------------------------------

app = FastAPI(
    title="YtGenius — YouTube Video Q&A Assistant",
    description="YtGenius 2.0 Backend API",
    version="2.0.0",
    lifespan=lifespan,
)


# --------------------------------
# Session middleware (for Google OAuth)
# --------------------------------

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SECRET_KEY,
)


# --------------------------------
# CORS configuration
# --------------------------------

origins = settings.all_cors_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"^chrome-extension://[a-zA-Z0-9_-]+$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------
# Include routers
# --------------------------------

app.include_router(
    auth.router
)

app.include_router(
    conversations.router
)

app.include_router(
    videos.router
)

app.include_router(
    questions.router
)

app.include_router(
    support.router
)


# --------------------------------
# Users alias endpoint
# --------------------------------

@app.get(
    "/users/me",
    response_model=UserResponse,
    tags=["Users"],
)
def get_users_me(
    current_user: User = Depends(get_current_user),
):
    return current_user


# --------------------------------
# Root endpoint
# --------------------------------

@app.get("/")
def root():
    return {
        "message": "YouTube Video Q&A Assistant API",
        "version": "2.0.0",
    }


# --------------------------------
# Health checks
# --------------------------------

@app.get("/health", tags=["Health"])
def health_check():
    return {
        "status": "healthy"
    }


@app.get("/health/live", tags=["Health"])
def health_live():
    return {
        "status": "ok"
    }


@app.get("/health/ready", tags=["Health"])
def health_ready(db: Session = Depends(get_db)):
    checks = {}

    try:
        db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:
        checks["database"] = f"unhealthy: {exc}"

    try:
        qdrant_store = QdrantVectorStore()
        if qdrant_store.is_healthy():
            checks["qdrant"] = "ok"
        else:
            checks["qdrant"] = "unhealthy: ping failed"
    except Exception as exc:
        checks["qdrant"] = f"unhealthy: {exc}"

    all_ok = all(v == "ok" for v in checks.values())
    status_code = 200 if all_ok else 503
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "ready" if all_ok else "unhealthy",
            "checks": checks,
        },
    )
