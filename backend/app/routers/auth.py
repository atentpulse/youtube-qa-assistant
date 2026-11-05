import logging
import os
import urllib.parse
from fastapi_mail.errors import ConnectionErrors

logger = logging.getLogger(__name__)

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
)

from fastapi.responses import RedirectResponse

from app.auth.google_oauth import oauth

from sqlalchemy.orm import Session

from app.database.database import get_db

from app.models.user import User

from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    UserResponse,
    UpdateProfileRequest,
    TokenResponse,
    RefreshTokenRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
)
from fastapi.security import HTTPAuthorizationCredentials

from app.services.email_service import EmailService

from app.services.auth_service import (
    AuthService,
)

from app.services.rag_service import RAGService
from app.dependencies import get_rag_service

from app.auth.dependencies import (
    get_current_user,
    optional_security,
)
from app.auth.jwt import (
    create_access_token,
    create_refresh_token,
    decode_token,
    JWTError,
    ExpiredSignatureError,
)


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


# --------------------------------
# Configuration
# --------------------------------

from app.core import settings

FRONTEND_URL = (
    os.getenv("FRONTEND_URL")
    or settings.FRONTEND_URL
    or "http://localhost:3000"
).rstrip("/")


auth_service = AuthService()
email_service = EmailService()


# --------------------------------
# Register user
# --------------------------------


@router.post(
    "/register",
    response_model=UserResponse,
)
async def register_user(
    request: RegisterRequest,
    db: Session = Depends(get_db),
):

    try:

        email = str(request.email).strip().lower()

        user = auth_service.register_user(
            db=db,
            username=request.username.strip(),
            email=email,
            password=request.password,
        )

        raw_token = auth_service.create_email_verification_token(
            db=db,
            user_id=user.id,
        )

        verification_url = (
            f"{FRONTEND_URL}/verify-email"
            f"?token={raw_token}"
        )

        try:
            await email_service.send_email_verification(
                email=user.email,
                verification_url=verification_url,
            )
        except ConnectionErrors as error:
            logger.error(
                "SMTP connection error sending verification email to %s: %s",
                email,
                type(error).__name__,
            )
            raise HTTPException(
                status_code=503,
                detail=(
                    "Account registered, but verification email could not be sent. "
                    "Please check your email configuration or use resend verification."
                ),
            )
        except Exception as error:
            logger.error(
                "Failed to send verification email to %s: %s",
                email,
                type(error).__name__,
            )
            raise HTTPException(
                status_code=503,
                detail=(
                    "Account registered, but verification email could not be sent. "
                    "Please check your email configuration or use resend verification."
                ),
            )

        return user

    except ValueError as error:

        raise HTTPException(
            status_code=400,
            detail=str(error),
        )


# --------------------------------
# Verify email
# --------------------------------


@router.get(
    "/verify-email",
)
def verify_email(
    token: str,
    db: Session = Depends(get_db),
):

    try:

        auth_service.verify_email(
            db=db,
            token=token,
        )

        return {
            "message": "Email verified successfully."
        }

    except ValueError as error:

        raise HTTPException(
            status_code=400,
            detail=str(error),
        )


# --------------------------------
# Resend verification email
# --------------------------------


@router.post(
    "/resend-verification",
)
async def resend_verification(
    request: ForgotPasswordRequest,
    db: Session = Depends(get_db),
):

    email = str(request.email).strip().lower()

    user = (
        db.query(User)
        .filter(User.email == email)
        .first()
    )

    # Always return the same response.
    # This prevents account enumeration.
    if not user:

        return {
            "message": (
                "If an unverified account exists for this email, "
                "a verification link has been sent."
            )
        }

    # Google accounts are already verified by Google.
    if user.auth_provider == "google":

        return {
            "message": (
                "If an unverified account exists for this email, "
                "a verification link has been sent."
            )
        }

    # Already verified
    if user.email_verified:

        return {
            "message": (
                "If an unverified account exists for this email, "
                "a verification link has been sent."
            )
        }

    raw_token = auth_service.create_email_verification_token(
        db=db,
        user_id=user.id,
    )

    verification_url = (
        f"{FRONTEND_URL}/verify-email"
        f"?token={raw_token}"
    )

    try:
        await email_service.send_email_verification(
            email=user.email,
            verification_url=verification_url,
        )
    except ConnectionErrors as error:
        logger.error(
            "SMTP connection error resending verification email to %s: %s",
            email,
            type(error).__name__,
        )
        raise HTTPException(
            status_code=503,
            detail=(
                "Verification email could not be sent due to an email service error. "
                "Please try again later."
            ),
        )
    except Exception as error:
        logger.error(
            "Failed to resend verification email to %s: %s",
            email,
            type(error).__name__,
        )
        raise HTTPException(
            status_code=503,
            detail=(
                "Verification email could not be sent due to an email service error. "
                "Please try again later."
            ),
        )

    return {
        "message": (
            "If an unverified account exists for this email, "
            "a verification link has been sent."
        )
    }


# --------------------------------
# Login user
# --------------------------------


@router.post(
    "/login",
    response_model=TokenResponse,
)
def login_user(
    request: LoginRequest,
    db: Session = Depends(get_db),
):

    try:

        email = str(request.email).strip().lower()
        access_token = auth_service.login_user(
            db=db,
            email=email,
            password=request.password,
        )

        user = db.query(User).filter(User.email == email).first()
        refresh_token = create_refresh_token(user.id) if user else None

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
        }

    except ValueError as error:

        raise HTTPException(
            status_code=401,
            detail=str(error),
        )


# --------------------------------
# Refresh token
# --------------------------------


@router.post(
    "/refresh",
    response_model=TokenResponse,
)
def refresh_token(
    request: RefreshTokenRequest | None = None,
    credentials: HTTPAuthorizationCredentials | None = Depends(optional_security),
    db: Session = Depends(get_db),
):

    user_id = None

    # Option 1: Dedicated refresh token in request body
    if request and request.refresh_token:
        raw_token = request.refresh_token.strip()
        try:
            payload = decode_token(raw_token)
        except ExpiredSignatureError:
            raise HTTPException(
                status_code=401,
                detail="Refresh token has expired. Please sign in again.",
            )
        except JWTError:
            raise HTTPException(
                status_code=401,
                detail="Invalid refresh token.",
            )

        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=401,
                detail="Token is not a valid refresh token.",
            )

        sub = payload.get("sub")
        if not sub:
            raise HTTPException(
                status_code=401,
                detail="Invalid refresh token claims.",
            )
        user_id = int(sub)

    # Option 2: Active Bearer token in header (existing frontend contract)
    elif credentials and credentials.credentials:
        raw_token = credentials.credentials.strip()
        try:
            payload = decode_token(raw_token)
        except ExpiredSignatureError:
            raise HTTPException(
                status_code=401,
                detail="Token has expired. Please sign in again.",
            )
        except JWTError:
            raise HTTPException(
                status_code=401,
                detail="Invalid authentication token.",
            )

        sub = payload.get("sub")
        if not sub:
            raise HTTPException(
                status_code=401,
                detail="Invalid token claims.",
            )
        user_id = int(sub)

    else:
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Provide a refresh_token or active Bearer token.",
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=401,
            detail="User associated with token no longer exists.",
        )

    new_access = create_access_token(user.id)
    new_refresh = create_refresh_token(user.id)

    return {
        "access_token": new_access,
        "refresh_token": new_refresh,
        "token_type": "bearer",
    }


# --------------------------------
# Google login
# --------------------------------


@router.get(
    "/google/login",
)
async def google_login(
    request: Request,
):

    redirect_uri = os.getenv(
        "GOOGLE_REDIRECT_URI"
    )

    if not redirect_uri:

        raise HTTPException(
            status_code=500,
            detail=(
                "Google OAuth redirect URI "
                "is not configured."
            ),
        )

    # Clear any stale OAuth session state to avoid mismatching state errors
    for key in list(request.session.keys()):
        if key.startswith("_state_google_") or key.startswith("_google_"):
            request.session.pop(key, None)

    return await oauth.google.authorize_redirect(
        request,
        redirect_uri,
    )


# --------------------------------
# Google OAuth callback
# --------------------------------


@router.get(
    "/google/callback"
)
async def google_callback(
    request: Request,
    db: Session = Depends(get_db),
):

    try:

        # Exchange authorization code
        # for Google tokens
        token = await oauth.google.authorize_access_token(
            request
        )

        # Get Google user information
        user_info = token.get("userinfo")

        if not user_info:
            try:
                user_info = await oauth.google.userinfo(token=token)
            except Exception as e:
                print(f"Fallback userinfo fetch failed: {e}")

        if not user_info:
            error_message = urllib.parse.quote(
                "Unable to retrieve Google user information."
            )
            return RedirectResponse(
                url=f"{FRONTEND_URL}/login?error={error_message}"
            )

        # Google must confirm that
        # the email is verified
        if not user_info.get("email_verified"):
            error_message = urllib.parse.quote(
                "Google email is not verified."
            )
            return RedirectResponse(
                url=f"{FRONTEND_URL}/login?error={error_message}"
            )

        google_id = user_info.get("sub") or user_info.get("id")
        email = user_info.get("email")

        if not google_id or not email:
            error_message = urllib.parse.quote(
                "Google account information is incomplete."
            )
            return RedirectResponse(
                url=f"{FRONTEND_URL}/login?error={error_message}"
            )

        username = (
            user_info.get("name")
            or email.split("@")[0]
        )

        # Create/login user and generate
        # application JWT
        access_token = (
            auth_service.login_or_create_google_user(
                db=db,
                google_id=google_id,
                email=email,
                username=username,
            )
        )

        return RedirectResponse(
            url=(
                f"{FRONTEND_URL}/oauth/callback"
                f"?token={urllib.parse.quote(access_token)}"
            )
        )

    except ValueError as error:

        error_message = urllib.parse.quote(
            str(error)
        )

        return RedirectResponse(
            url=(
                f"{FRONTEND_URL}/login"
                f"?error={error_message}"
            )
        )

    except Exception as error:

        print(
            "Google OAuth callback error: "
            f"{type(error).__name__}: {error}"
        )

        error_message = urllib.parse.quote(
            "Google authentication failed."
        )

        return RedirectResponse(
            url=(
                f"{FRONTEND_URL}/login"
                f"?error={error_message}"
            )
        )


# --------------------------------
# Get current user
# --------------------------------


@router.get(
    "/me",
    response_model=UserResponse,
)
def get_current_user_info(
    current_user: User = Depends(
        get_current_user
    ),
):

    return current_user


@router.patch(
    "/me",
    response_model=UserResponse,
)
def update_current_user_profile(
    request: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    new_username = request.username.strip()
    if not new_username:
        raise HTTPException(
            status_code=400,
            detail="Username cannot be blank.",
        )
    current_user.username = new_username
    db.commit()
    db.refresh(current_user)
    return current_user


@router.delete(
    "/me",
)
def delete_current_user_account(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    rag_service: RAGService = Depends(get_rag_service),
):
    # 1. Clean up user videos through reference-counted deletion
    for uv in list(current_user.user_videos):
        try:
            rag_service.delete_video(
                db=db,
                user_id=current_user.id,
                video_id=uv.video_id,
            )
        except Exception as e:
            logger.warning(
                f"Error unlinking video {uv.video_id} during account deletion: {e}"
            )

    # 2. Delete user and commit (cascades to orphaned conversations and auth tokens)
    db.delete(current_user)
    db.commit()

    return {"message": "Account deleted successfully."}


# --------------------------------
# Forgot password
# --------------------------------


@router.post(
    "/forgot-password",
)
async def forgot_password(
    request: ForgotPasswordRequest,
    db: Session = Depends(get_db),
):

    email = str(request.email).strip().lower()

    user, raw_token = (
        auth_service.create_password_reset_token(
            db=db,
            email=email,
        )
    )

    # Always return the same response
    # whether the email exists or not.
    if user and raw_token:

        reset_url = (
            f"{FRONTEND_URL}/reset-password"
            f"?token={raw_token}"
        )

        try:
            await email_service.send_password_reset_email(
                email=user.email,
                reset_url=reset_url,
            )
        except ConnectionErrors as error:
            logger.error(
                "SMTP connection error sending password reset email to %s: %s",
                email,
                type(error).__name__,
            )
            raise HTTPException(
                status_code=503,
                detail=(
                    "Password reset email could not be sent due to an email service error. "
                    "Please try again later."
                ),
            )
        except Exception as error:
            logger.error(
                "Failed to send password reset email to %s: %s",
                email,
                type(error).__name__,
            )
            raise HTTPException(
                status_code=503,
                detail=(
                    "Password reset email could not be sent due to an email service error. "
                    "Please try again later."
                ),
            )

    return {
        "message": (
            "If an account exists for this email, "
            "a password reset link has been sent."
        )
    }


# --------------------------------
# Reset password
# --------------------------------


@router.post(
    "/reset-password",
)
def reset_password(
    request: ResetPasswordRequest,
    db: Session = Depends(get_db),
):

    try:

        auth_service.reset_password(
            db=db,
            token=request.token,
            new_password=request.new_password,
        )

        return {
            "message": "Password reset successfully."
        }

    except ValueError as error:

        raise HTTPException(
            status_code=400,
            detail=str(error),
        )