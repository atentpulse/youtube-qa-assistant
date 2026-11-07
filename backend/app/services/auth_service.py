from sqlalchemy import func
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
            if existing_user.email_verified:
                raise ValueError("Email is already registered.")

            # Unverified account retry: update credentials and allow re-registration
            existing_user.username = username
            existing_user.password_hash = hash_password(password)
            existing_user.auth_provider = "local"
            db.commit()
            db.refresh(existing_user)
            return existing_user

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
            token_version=user.token_version or 1,
        )

        return access_token

    def login_or_create_google_user(
        self,
        db: Session,
        google_id: str,
        email: str,
        username: str,
    ) -> str:
        clean_email = email.strip().lower()
        gid = str(google_id).strip()

        # 1. Stable primary identity: Match by Google ID
        user = db.query(User).filter(User.google_id == gid).first()

        if user:
            # Sync email if changed on Google and guarantee verified status
            if user.email.lower() != clean_email:
                user.email = clean_email
            user.email_verified = True
            db.commit()
            return create_access_token(
                user_id=user.id,
                token_version=user.token_version or 1,
            )

        # 2. Match by verified email (case-insensitive)
        existing_user = (
            db.query(User)
            .filter(func.lower(User.email) == clean_email)
            .first()
        )

        if existing_user:
            # Link Google account if not yet linked to a different google_id
            if not existing_user.google_id:
                existing_user.google_id = gid
                existing_user.email_verified = True
                db.commit()
                return create_access_token(
                    user_id=existing_user.id,
                    token_version=existing_user.token_version or 1,
                )
            elif existing_user.google_id == gid:
                existing_user.email_verified = True
                db.commit()
                return create_access_token(
                    user_id=existing_user.id,
                    token_version=existing_user.token_version or 1,
                )
            else:
                raise ValueError(
                    "This email is already associated with another Google account."
                )

        # 3. Create a new Google user
        new_user = User(
            username=(username or clean_email.split("@")[0])[:100],
            email=clean_email,
            password_hash=None,
            auth_provider="google",
            google_id=gid,
            email_verified=True,
        )

        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        return create_access_token(
            user_id=new_user.id,
            token_version=new_user.token_version or 1,
        )

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
        user.token_version = (user.token_version or 1) + 1

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
