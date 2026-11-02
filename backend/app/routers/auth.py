import os
import urllib.parse

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

FRONTEND_URL = os.getenv(
    "FRONTEND_URL",
    "http://localhost:5173",
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

        await email_service.send_email_verification(
            email=user.email,
            verification_url=verification_url,
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

    await email_service.send_email_verification(
        email=user.email,
        verification_url=verification_url,
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

            raise HTTPException(
                status_code=400,
                detail=(
                    "Unable to retrieve Google "
                    "user information."
                ),
            )

        # Google must confirm that
        # the email is verified
        if not user_info.get("email_verified"):

            raise HTTPException(
                status_code=400,
                detail=(
                    "Google email is not verified."
                ),
            )

        google_id = user_info.get("sub")
        email = user_info.get("email")

        if not google_id or not email:

            raise HTTPException(
                status_code=400,
                detail=(
                    "Google account information "
                    "is incomplete."
                ),
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

    except HTTPException:

        raise

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

        await email_service.send_password_reset_email(
            email=user.email,
            reset_url=reset_url,
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