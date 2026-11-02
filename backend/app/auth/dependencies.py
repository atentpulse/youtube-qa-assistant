from fastapi import (
    Depends,
    HTTPException,
    status,
)

from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)

from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.auth.jwt import (
    ALGORITHM,
    SECRET_KEY,
)

from app.database.database import (
    get_db,
)

from app.models.user import User


security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(
        security
    ),
    db: Session = Depends(
        get_db
    ),
) -> User:

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired authentication token.",
    )

    try:

        token = credentials.credentials

        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
        )

        user_id = payload.get(
            "sub"
        )

        if user_id is None:

            raise credentials_exception

        if payload.get("type") == "refresh":

            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token cannot be used for API access. Use an access token.",
            )

        user_id = int(
            user_id
        )

    except (
        JWTError,
        ValueError,
    ):

        raise credentials_exception


    user = (
        db.query(User)
        .filter(
            User.id == user_id
        )
        .first()
    )

    if user is None:

        raise credentials_exception

    return user


# --------------------------------
# Get current user optionally
# --------------------------------

optional_security = HTTPBearer(
    auto_error=False
)


def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials | None = Depends(
        optional_security
    ),
    db: Session = Depends(
        get_db
    ),
) -> User | None:

    # No token → guest user
    if credentials is None:

        return None

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired authentication token.",
    )

    try:

        token = credentials.credentials

        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
        )

        user_id = payload.get(
            "sub"
        )

        if user_id is None:

            raise credentials_exception

        user_id = int(
            user_id
        )

    except (
        JWTError,
        ValueError,
    ):

        raise credentials_exception


    user = (
        db.query(User)
        .filter(
            User.id == user_id
        )
        .first()
    )

    if user is None:

        raise credentials_exception

    return user