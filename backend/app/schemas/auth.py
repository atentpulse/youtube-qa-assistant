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

    auth_provider: str = "local"

    role: str = "user"

    created_at: datetime | None = None


class UpdateProfileRequest(BaseModel):

    username: str = Field(
        min_length=2,
        max_length=100,
    )


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


class OAuthExchangeRequest(BaseModel):
    code: str = Field(
        min_length=1,
        max_length=200,
    )


class SendOTPRequest(BaseModel):
    email: EmailStr


class SendOTPResponse(BaseModel):
    message: str
    cooldown_seconds: int = 60


class VerifyOTPRequest(BaseModel):
    email: EmailStr
    otp: str = Field(
        min_length=6,
        max_length=6,
        pattern=r"^\d{6}$",
        description="6-digit numeric login code",
    )
