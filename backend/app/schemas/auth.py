from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegisterRequest(BaseModel):

    username: str = Field(
        min_length=3,
        max_length=100,
    )

    email: EmailStr

    password: str = Field(
        min_length=6,
        max_length=100,
    )


class LoginRequest(BaseModel):

    email: EmailStr

    password: str


class UserResponse(BaseModel):

    model_config = ConfigDict(from_attributes=True)

    id: int

    username: str

    email: EmailStr

    email_verified: bool = False

    created_at: datetime | None = None


class TokenResponse(BaseModel):

    access_token: str

    token_type: str = "bearer"

    refresh_token: str | None = None


class RefreshTokenRequest(BaseModel):

    refresh_token: str | None = None


class ForgotPasswordRequest(BaseModel):

    email: EmailStr


class ResetPasswordRequest(BaseModel):

    token: str = Field(
        min_length=1,
        max_length=500,
    )

    new_password: str = Field(
        min_length=6,
        max_length=100,
    )
