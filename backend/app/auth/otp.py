"""Cryptographic OTP generation, hashing, and verification utilities."""

import hashlib
import hmac
import secrets

from app.core.config import settings


def generate_otp_code() -> str:
    """Generate a cryptographically secure 6-digit numeric one-time password."""
    return f"{secrets.randbelow(1_000_000):06d}"


def hash_otp_code(email: str, otp: str) -> str:
    """Compute an HMAC-SHA256 hash of the OTP bound to the normalized email address.

    Binding the OTP to the email address and signing with the server SECRET_KEY ensures
    that precomputed rainbow tables cannot be used against the numeric search space.
    """
    secret = (settings.SECRET_KEY or "ytgenius-otp-secret-key").encode("utf-8")
    payload = f"{email.strip().lower()}:{otp.strip()}".encode("utf-8")
    return hmac.new(secret, payload, hashlib.sha256).hexdigest()


def verify_otp_code(email: str, otp: str, stored_hash: str) -> bool:
    """Perform constant-time verification of a candidate OTP against the stored hash."""
    if not otp or not stored_hash:
        return False
    candidate_hash = hash_otp_code(email, otp)
    return hmac.compare_digest(candidate_hash, stored_hash)
