from sqlalchemy import func
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models.user import User

from app.auth.password import hash_password, verify_password

from app.auth.jwt import (
    create_access_token,
    create_refresh_token,
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

from app.auth.otp import generate_otp_code, hash_otp_code, verify_otp_code
from app.models.email_otp import EmailOTP
from app.core.config import settings


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
            raise ValueError(
                "An unverified account with this email already exists. "
                "Please check your inbox or request a new verification email."
            )

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

        try:
            db.add(user)
            db.commit()
            db.refresh(user)
        except IntegrityError:
            db.rollback()
            raise ValueError("Email is already registered.")

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

        reset_expire_minutes = getattr(settings, "PASSWORD_RESET_TOKEN_EXPIRE_MINUTES", 30)
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=reset_expire_minutes)

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

        # Atomically consume the token to prevent concurrent reuse
        updated = (
            db.query(PasswordResetToken)
            .filter(
                PasswordResetToken.id == reset_token.id,
                PasswordResetToken.used_at.is_(None),
            )
            .update({PasswordResetToken.used_at: now}, synchronize_session="fetch")
        )
        if updated == 0:
            raise ValueError("Invalid or expired password reset token.")

        user.password_hash = hash_password(new_password)
        user.token_version = (user.token_version or 1) + 1

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

        verify_expire_minutes = getattr(settings, "EMAIL_VERIFICATION_TOKEN_EXPIRE_MINUTES", 30)
        expires_at = now + timedelta(minutes=verify_expire_minutes)

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

        # Atomically consume the verification token
        updated = (
            db.query(EmailVerificationToken)
            .filter(
                EmailVerificationToken.id == verification_token.id,
                EmailVerificationToken.used_at.is_(None),
            )
            .update({EmailVerificationToken.used_at: now}, synchronize_session="fetch")
        )
        if updated == 0:
            raise ValueError("Verification token has already been used.")

        user.email_verified = True

        db.commit()

    def send_login_otp(
        self,
        db: Session,
        email: str,
    ) -> tuple[str, int]:
        """Generate a 6-digit OTP, store its HMAC hash, and return (raw_otp, cooldown_seconds).

        Enforces a 60-second resend cooldown and invalidates previous unused codes.
        """
        clean_email = email.strip().lower()
        now = datetime.now(timezone.utc)

        # Check resend cooldown
        recent_otp = (
            db.query(EmailOTP)
            .filter(EmailOTP.email == clean_email)
            .order_by(EmailOTP.created_at.desc())
            .first()
        )
        if recent_otp:
            created_at = recent_otp.created_at
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
            elapsed = (now - created_at).total_seconds()
            if elapsed < 60.0:
                cooldown_remaining = max(1, int(60.0 - elapsed))
                raise ValueError(
                    f"Please wait {cooldown_remaining} seconds before requesting another code."
                )

        # Invalidate previous unused OTPs for this email address
        db.query(EmailOTP).filter(
            EmailOTP.email == clean_email,
            EmailOTP.used_at.is_(None),
        ).update({EmailOTP.used_at: now}, synchronize_session=False)

        # Generate cryptographically secure 6-digit code and store its hash
        raw_otp = generate_otp_code()
        otp_hash = hash_otp_code(clean_email, raw_otp)
        otp_expire_minutes = getattr(settings, "OTP_EXPIRE_MINUTES", 5)
        cooldown_seconds = getattr(settings, "OTP_RESEND_COOLDOWN_SECONDS", 60)
        max_attempts = getattr(settings, "OTP_MAX_ATTEMPTS", 5)
        expires_at = now + timedelta(minutes=otp_expire_minutes)

        otp_record = EmailOTP(
            email=clean_email,
            otp_hash=otp_hash,
            expires_at=expires_at,
            attempts=0,
            max_attempts=max_attempts,
        )
        db.add(otp_record)
        db.commit()

        return raw_otp, cooldown_seconds

    def verify_login_otp(
        self,
        db: Session,
        email: str,
        otp: str,
    ) -> tuple[User, str, str]:
        """Verify the 6-digit OTP code against the stored hash and authenticate or register user.

        Returns (user, access_token, refresh_token).
        """
        clean_email = email.strip().lower()
        clean_otp = otp.strip()
        now = datetime.now(timezone.utc)

        active_otp = (
            db.query(EmailOTP)
            .filter(
                EmailOTP.email == clean_email,
                EmailOTP.used_at.is_(None),
            )
            .order_by(EmailOTP.created_at.desc())
            .first()
        )

        if not active_otp:
            raise ValueError("Invalid or expired login code. Please request a new code.")

        # Check expiration
        expires_at = active_otp.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        if expires_at <= now:
            active_otp.used_at = now
            db.commit()
            raise ValueError("Login code has expired. Please request a new code.")

        # Check attempt limits
        if active_otp.attempts >= active_otp.max_attempts:
            active_otp.used_at = now
            db.commit()
            raise ValueError(
                "Too many incorrect attempts. This code is now invalid. Please request a new one."
            )

        # Verify code
        if not verify_otp_code(clean_email, clean_otp, active_otp.otp_hash):
            active_otp.attempts += 1
            if active_otp.attempts >= active_otp.max_attempts:
                active_otp.used_at = now
                db.commit()
                raise ValueError(
                    "Too many incorrect attempts. This code is now invalid. Please request a new one."
                )
            remaining = active_otp.max_attempts - active_otp.attempts
            db.commit()
            raise ValueError(f"Invalid login code. {remaining} attempt(s) remaining.")

        # Atomically consume the OTP
        updated = (
            db.query(EmailOTP)
            .filter(
                EmailOTP.id == active_otp.id,
                EmailOTP.used_at.is_(None),
            )
            .update({EmailOTP.used_at: now}, synchronize_session="fetch")
        )
        if updated == 0:
            raise ValueError("Login code has already been used. Please request a new one.")

        # Existing account or new account creation
        user = db.query(User).filter(func.lower(User.email) == clean_email).first()

        if user:
            # Preserve existing user, ensure email is verified
            if not user.email_verified:
                user.email_verified = True
        else:
            # New user creation
            username = clean_email.split("@")[0][:100]
            user = User(
                username=username,
                email=clean_email,
                password_hash=None,
                auth_provider="email_otp",
                email_verified=True,
            )
            db.add(user)

        db.commit()
        db.refresh(user)

        # Generate JWT session tokens
        access_token = create_access_token(
            user_id=user.id,
            token_version=user.token_version or 1,
        )
        refresh_token = create_refresh_token(
            user_id=user.id,
            token_version=user.token_version or 1,
        )

        return user, access_token, refresh_token
