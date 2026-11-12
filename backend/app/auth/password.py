import bcrypt

MAX_BCRYPT_BYTES = 72


def hash_password(
    password: str,
) -> str:
    """
    Hashes a password using bcrypt.
    Enforces a strict 72 UTF-8 byte maximum length for newly created or changed passwords.
    """
    if not password:
        raise ValueError("Password cannot be empty.")
    pwd_bytes = password.encode("utf-8")
    if len(pwd_bytes) > MAX_BCRYPT_BYTES:
        raise ValueError(
            f"Password exceeds maximum allowed length of {MAX_BCRYPT_BYTES} bytes."
        )
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def verify_password(
    plain_password: str,
    hashed_password: str,
) -> bool:
    """
    Verifies a plain password against a bcrypt hash.
    Preserves verification compatibility for existing Passlib-generated $2a$ and $2b$ hashes,
    including legacy passwords that were previously truncated at 72 UTF-8 bytes.
    """
    if not plain_password or not hashed_password:
        return False
    try:
        # Legacy Passlib compatibility: Passlib truncated secrets at 72 UTF-8 bytes
        # when hashing. Slicing [:MAX_BCRYPT_BYTES] ensures that existing accounts
        # with legacy passwords > 72 bytes can continue authenticating without interruption.
        pwd_bytes = plain_password.encode("utf-8")[:MAX_BCRYPT_BYTES]
        hash_bytes = hashed_password.encode("utf-8")
        return bcrypt.checkpw(pwd_bytes, hash_bytes)
    except Exception:
        return False
