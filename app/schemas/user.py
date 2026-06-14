"""Pydantic schemas for users and authentication."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserSchema(BaseModel):
    """Base schema config shared by user/auth schemas."""

    model_config = ConfigDict(
        from_attributes=True,
        str_strip_whitespace=True,
        extra="forbid",
    )


class UserCreate(UserSchema):
    """Payload used to create a new user."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserLogin(UserSchema):
    """Payload used to authenticate a user."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserResponse(UserSchema):
    """User representation returned by the API."""

    id: int
    email: EmailStr
    is_active: bool
    is_verified: bool
    avatar_url: str | None = None
    created_at: datetime
    updated_at: datetime


class TokenResponse(UserSchema):
    """JWT access token response."""

    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"


class RefreshTokenRequest(UserSchema):
    """Payload used to exchange a refresh token for a new token pair."""

    refresh_token: str


class EmailRequest(UserSchema):
    """Payload for endpoints that accept an email address only."""

    email: EmailStr


class PasswordResetRequest(UserSchema):
    """Payload for requesting a password reset."""

    email: EmailStr


class PasswordResetUpdate(UserSchema):
    """Payload for updating password via reset token."""

    token: str
    password: str = Field(min_length=8, max_length=128)
