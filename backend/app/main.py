import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.auth.dependencies import get_current_user
from app.core import settings
from app.database.database import engine
from app.models import (
    User,
    Conversation,
    Message,
    Video,
    UserVideo,
    QuestionCache,
    PasswordResetToken,
    EmailVerificationToken,
)
from app.routers import (
    auth,
    conversations,
    videos,
    questions,
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
# Health check
# --------------------------------

@app.get("/health")
def health_check():
    return {
        "status": "healthy"
    }
