from sqlalchemy.orm import Session

from app.models.user import User

from app.auth.password import hash_password, verify_password

from app.auth.jwt import (
    create_access_token,
)

from datetime import datetime, timedelta, timezone

from app.auth.password_reset import generate_reset_token
from app.models.password_reset_token import PasswordResetToken
from app.auth.password_reset import hash_reset_token

from app.auth.email_verification import (
    generate_verification_token,
    hash_verification_token,
)
from app.models.email_verification_token import EmailVerificationToken


class AuthService:

    def register_user(
        self,
        db: Session,
        username: str,
        email: str,
        password: str,
    ) -> User:

        # Check existing email
        existing_user = db.query(User).filter(User.email == email).first()

        if existing_user:
            raise ValueError("Email is already registered.")

        # Hash password
        hashed_password = hash_password(password)

        # Create user
        user = User(
            username=username,
            email=email,
            password_hash=hashed_password,
            auth_provider="local",
            email_verified=False,
        )

        db.add(user)

        db.commit()
        db.refresh(user)

        return user

    def login_user(
        self,
        db: Session,
        email: str,
        password: str,
    ) -> str:

        user = db.query(User).filter(User.email == email).first()

        if not user:
            raise ValueError("Invalid email or password.")

        if user.auth_provider != "local":
            raise ValueError("Invalid email or password.")

        if not user.password_hash:
            raise ValueError("Invalid email or password.")

        if not verify_password(
            password,
            user.password_hash,
        ):
            raise ValueError("Invalid email or password.")

        if not user.email_verified:
            raise ValueError("Please verify your email before logging in.")

        access_token = create_access_token(
            user_id=user.id,
        )

        return access_token

    def login_or_create_google_user(
        self,
        db: Session,
        google_id: str,
        email: str,
        username: str,
    ) -> str:

        # 1. Find existing Google user by Google ID
        user = db.query(User).filter(User.google_id == google_id).first()

        # Existing Google user → login
        if user:
            return create_access_token(
                user_id=user.id,
            )

        # 2. Check whether this email already belongs to a user
        existing_user = db.query(User).filter(User.email == email).first()

        # Existing local account → do NOT silently link
        if existing_user:
            raise ValueError(
                "An account with this email already exists. "
                "Please log in using your existing account."
            )

        # 3. Create a new Google user
        user = User(
            username=username[:100],
            email=email,
            password_hash=None,
            auth_provider="google",
            google_id=google_id,
            email_verified=True,
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        # 4. Issue your normal application JWT
        access_token = create_access_token(
            user_id=user.id,
        )

        return access_token

    def create_password_reset_token(
        self,
        db: Session,
        email: str,
    ) -> tuple[User | None, str | None]:

        user = (
            db.query(User)
            .filter(
                User.email == email,
                User.auth_provider == "local",
            )
            .first()
        )

        if not user:
            return None, None

        raw_token, token_hash = generate_reset_token()

        expires_at = datetime.now(timezone.utc) + timedelta(minutes=30)

        reset_token = PasswordResetToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at,
        )

        db.add(reset_token)
        db.commit()

        return user, raw_token

    def reset_password(
        self,
        db: Session,
        token: str,
        new_password: str,
    ) -> None:

        token_hash = hash_reset_token(token)

        reset_token = (
            db.query(PasswordResetToken)
            .filter(PasswordResetToken.token_hash == token_hash)
            .first()
        )

        if not reset_token:
            raise ValueError("Invalid or expired password reset token.")

        now = datetime.now(timezone.utc)

        if reset_token.used_at is not None:
            raise ValueError("Invalid or expired password reset token.")

        expires_at = reset_token.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at <= now:
            raise ValueError("Invalid or expired password reset token.")

        user = db.query(User).filter(User.id == reset_token.user_id).first()

        if not user:
            raise ValueError("Invalid or expired password reset token.")

        user.password_hash = hash_password(new_password)

        reset_token.used_at = now

        db.commit()

    def create_email_verification_token(
        self,
        db: Session,
        user_id: int,
    ) -> str:

        # Invalidate previous unused verification tokens
        now = datetime.now(timezone.utc)

        existing_tokens = (
            db.query(EmailVerificationToken)
            .filter(
                EmailVerificationToken.user_id == user_id,
                EmailVerificationToken.used_at.is_(None),
            )
            .all()
        )

        for existing_token in existing_tokens:
            existing_token.used_at = now

        # Create a new verification token
        raw_token, token_hash = generate_verification_token()

        expires_at = now + timedelta(minutes=30)

        verification_token = EmailVerificationToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )

        db.add(verification_token)
        db.commit()

        return raw_token

    def verify_email(
        self,
        db,
        token: str,
    ) -> None:
        token_hash = hash_verification_token(token)

        verification_token = (
            db.query(EmailVerificationToken)
            .filter(EmailVerificationToken.token_hash == token_hash)
            .first()
        )

        if not verification_token:
            raise ValueError("Invalid or expired verification token.")

        now = datetime.now(timezone.utc)

        if verification_token.used_at is not None:
            raise ValueError("Verification token has already been used.")

        expires_at = verification_token.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at <= now:
            raise ValueError("Verification token has expired.")

        user = db.query(User).filter(User.id == verification_token.user_id).first()

        if not user:
            raise ValueError("User not found.")

        user.email_verified = True
        verification_token.used_at = now

        db.commit()
