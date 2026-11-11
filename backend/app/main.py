import os
import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
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

is_production = (settings.ENVIRONMENT or "").strip().lower() in ("production", "prod")

app = FastAPI(
    title="YtGenius — YouTube Video Q&A Assistant",
    description="YtGenius 2.0 Backend API",
    version="2.0.0",
    lifespan=lifespan,
    docs_url=None if is_production else "/docs",
    redoc_url=None if is_production else "/redoc",
    openapi_url=None if is_production else "/openapi.json",
)


# --------------------------------
# Request body size limit middleware
# --------------------------------

@app.middleware("http")
async def limit_request_size(request: Request, call_next):
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            max_size = getattr(settings, "MAX_REQUEST_BODY_SIZE_BYTES", 10 * 1024 * 1024)
            if int(content_length) > max_size:
                return JSONResponse(
                    status_code=413,
                    content={"detail": "Request payload too large. Maximum allowed size is 10MB."},
                )
        except (ValueError, TypeError):
            pass
    try:
        return await call_next(request)
    except Exception as exc:
        logging.getLogger(__name__).error(
            "Unhandled server exception during %s %s: %s",
            request.method,
            request.url.path,
            exc,
            exc_info=True,
        )
        return JSONResponse(
            status_code=500,
            content={"detail": "An internal server error occurred. Please try again later."},
        )


# --------------------------------
# Session middleware (for Google OAuth)
# --------------------------------

session_secret = getattr(settings, "SESSION_SECRET_KEY", None) or settings.SECRET_KEY

app.add_middleware(
    SessionMiddleware,
    secret_key=session_secret,
    https_only=is_production,
    same_site="lax",
)


# --------------------------------
# Dynamic CORS configuration
# --------------------------------

class DynamicCORSMiddleware(CORSMiddleware):
    """Subclass of Starlette's CORSMiddleware that evaluates origins against

    settings.all_cors_origins dynamically, ensuring dynamically added
    extension IDs or origins in settings are honored without accepting arbitrary
    extensions.
    """

    def is_allowed_origin(self, origin: str) -> bool:
        if origin in settings.all_cors_origins:
            return True
        return super().is_allowed_origin(origin)


origins = settings.all_cors_origins

app.add_middleware(
    DynamicCORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------
# Global exception handler
# Guarantees CORS headers are attached on unhandled exceptions
# --------------------------------

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logging.getLogger(__name__).error(
        "Unhandled server exception during %s %s: %s",
        request.method,
        request.url.path,
        exc,
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred. Please try again later."},
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
        logging.getLogger(__name__).error("Database readiness check failed: %s", exc, exc_info=True)
        checks["database"] = "unhealthy: database check failed"

    try:
        qdrant_store = QdrantVectorStore()
        if qdrant_store.is_healthy():
            checks["qdrant"] = "ok"
        else:
            checks["qdrant"] = "unhealthy: ping failed"
    except Exception as exc:
        logging.getLogger(__name__).error("Qdrant readiness check failed: %s", exc, exc_info=True)
        checks["qdrant"] = "unhealthy: vector store check failed"

    all_ok = all(v == "ok" for v in checks.values())
    status_code = 200 if all_ok else 503
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "ready" if all_ok else "unhealthy",
            "checks": checks,
        },
    )
