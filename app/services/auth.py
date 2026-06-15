"""Business logic for authentication operations."""

import bcrypt
import hashlib

from typing import Optional, Literal
from datetime import UTC, datetime, timedelta
from jose import jwt
from jose.exceptions import JWTError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.redis import cache_current_user, invalidate_current_user_cache
from app.exceptions import (
    InvalidCredentialsError,
    UserAlreadyExistsError,
    UserNotFoundError,
)
from app.repositories.user import UserRepository
from app.schemas.user import (
    RefreshTokenRequest,
    TokenResponse,
    UserCreate,
    UserLogin,
    UserResponse,
    PasswordResetRequest,
    PasswordResetUpdate,
)
from app.services.avatar import build_gravatar_url
from app.services.mailer import send_verification_email as send_verification_email_async


def hash_password(password: str) -> str:
    pwd_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(
        plain_password.encode("utf-8"), hashed_password.encode("utf-8")
    )


def create_token(
    subject: str, expiry_delta: timedelta, token_type: Literal["access", "refresh", "email_verification", "password_reset"]
) -> str:
    """Create a signed JWT token with the given subject, expiry, and optional type."""

    settings = get_settings()
    now = datetime.now(UTC)
    expire = now + expiry_delta
    payload = {"sub": subject, "exp": expire, "iat": now, "type": token_type}

    return jwt.encode(
        payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )


def create_access_token(subject: str, expires_delta: Optional[float]=None) -> str:
    """Create a signed JWT access token for the given subject."""

    settings = get_settings()
    expire_minutes = expires_delta or timedelta(minutes=settings.access_token_expire_minutes)

    refresh_token = create_token(subject, expire_minutes, "access")

    return refresh_token


def create_refresh_token(subject: str, expires_delta: Optional[float]=None) -> str:
    """Create a signed JWT refresh token for the given subject."""

    settings = get_settings()
    expire_minutes = expires_delta or timedelta(minutes=settings.refresh_token_expire_days * 24 * 60)

    refresh_token = create_token(subject, expire_minutes, "refresh")

    return refresh_token


def create_email_verification_token(subject: str) -> str:
    """Create a time-limited token used for email verification."""

    settings = get_settings()

    return create_token(
        subject,
        timedelta(hours=settings.email_verification_token_expire_hours),
        token_type="email_verification",
    )


def create_password_reset_token(subject: str) -> str:
    """Create a time-limited token used for password reset."""

    settings = get_settings()

    return create_token(
        subject,
        timedelta(minutes=settings.password_reset_token_expire_minutes),
        token_type="password_reset",
    )


def decode_email_verification_token(token: str) -> str:
    """Decode and validate an email verification token, returning the subject."""

    settings = get_settings()
    payload = jwt.decode(
        token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
    )
    if payload.get("type") != "email_verification":
        raise InvalidCredentialsError("Invalid verification token")
    subject = payload.get("sub")
    if not subject or not isinstance(subject, str):
        raise InvalidCredentialsError("Invalid verification token")
    return subject


def decode_password_reset_token(token: str) -> str:
    """Decode and validate a password reset token, returning the subject."""

    settings = get_settings()
    payload = jwt.decode(
        token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
    )
    if payload.get("type") != "password_reset":
        raise InvalidCredentialsError("Invalid password reset token")
    subject = payload.get("sub")
    if not subject or not isinstance(subject, str):
        raise InvalidCredentialsError("Invalid password reset token")
    return subject


def decode_access_token(token: str) -> str:
    """Decode and validate a JWT access token, returning the subject."""

    settings = get_settings()
    payload = jwt.decode(
        token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
    )
    if payload.get("type") != "access":
        raise InvalidCredentialsError("Invalid access token")
    subject = payload.get("sub")
    if not subject or not isinstance(subject, str):
        raise InvalidCredentialsError("Invalid access token")
    return subject


def decode_refresh_token(token: str) -> str:
    """Decode and validate a JWT refresh token, returning the user."""

    settings = get_settings()
    payload = jwt.decode(
        token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
    )
    if payload.get("type") != "refresh":
        raise InvalidCredentialsError("Invalid refresh token")
    subject = payload.get("sub")
    if not subject or not isinstance(subject, str):
        raise InvalidCredentialsError("Invalid refresh token")
    return subject


def hash_token(token: str) -> str:
    """Return a stable hash for storing token material securely."""

    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _ensure_aware(value: datetime) -> datetime:
    """Normalize a datetime value to UTC if the database returned it without tzinfo."""

    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


class AuthService:
    """Business logic for user registration and authentication."""

    def __init__(self, session: AsyncSession) -> None:
        self.repository = UserRepository(session)
        self.session = session

    async def _commit_and_refresh(self, user) -> None:
        try:
            await self.session.commit()
            await self.session.refresh(user)
        except IntegrityError as exc:
            await self.session.rollback()
            raise UserAlreadyExistsError("User with this email already exists") from exc

    async def _ensure_email_is_available(self, email: str) -> None:
        existing_user = await self.repository.get_user_by_email(email)
        if existing_user:
            raise UserAlreadyExistsError("User with this email already exists")

    def _build_token_pair(self, subject: str, old_refresh_token: str=None) -> TokenResponse:
        access_token = create_access_token(subject=subject)
        refresh_token = old_refresh_token or create_refresh_token(subject=subject)
        return TokenResponse(access_token=access_token, refresh_token=refresh_token)

    async def register_user(self, user_in: UserCreate) -> UserResponse:
        """Create a new user with a hashed password."""

        try:
            await self._ensure_email_is_available(user_in.email)
            user = await self.repository.create_user(
                email=user_in.email,
                hashed_password=hash_password(user_in.password),
                avatar_url=build_gravatar_url(user_in.email),
            )
            await self._commit_and_refresh(user)
        except IntegrityError as exc:
            await self.session.rollback()
            raise UserAlreadyExistsError("User with this email already exists") from exc
        return UserResponse.model_validate(user)

    async def send_verification_email(self, user, host: str) -> None:
        """Generate a verification token and send it to the user's email using fastapi-mail."""

        token = create_email_verification_token(user.email)
        settings = get_settings()
        host = host.rstrip("/")  # Remove trailing slash from request.base_url
        verify_path = f"{settings.api_v1_prefix}/auth/verify?token={token}"
        link = f"{host}{verify_path}"

        template_data = {"link": link, "app_name": settings.app_name}
        await send_verification_email_async(
            user.email, "Verify your email", template_data
        )

    async def verify_email(self, token: str) -> UserResponse:
        """Verify the email using the provided token and mark the user verified."""

        try:
            email = decode_email_verification_token(token)
        except JWTError:
            raise InvalidCredentialsError("Invalid or expired verification token")

        user = await self.repository.get_user_by_email(email)
        if user is None:
            raise UserNotFoundError("User not found or email does not match token")

        # Skip commit if already verified
        if user.is_verified:
            return UserResponse.model_validate(user)

        user.is_verified = True
        await self._commit_and_refresh(user)
        return UserResponse.model_validate(user)

    async def login_user(self, user_in: UserLogin) -> TokenResponse:
        """Validate user credentials and return a token pair."""

        user = await self.repository.get_user_by_email(user_in.email)
        if user is None or not verify_password(user_in.password, user.hashed_password):
            raise InvalidCredentialsError("Invalid email or password")
        if not user.is_verified:
            raise InvalidCredentialsError("Email address is not verified")

        token_pair = self._build_token_pair(subject=user.email)
        user.refresh_token_hash = hash_token(token_pair.refresh_token)
        user.refresh_token_expires_at = datetime.now(UTC) + timedelta(
            days=get_settings().refresh_token_expire_days
        )
        await self._commit_and_refresh(user)
        await cache_current_user(token_pair.access_token, user)
        return token_pair
    
    async def logout_user(self, user, token: str | None = None) -> None:
        """Invalidate the user's refresh token by clearing the stored hash and expiry."""

        user.refresh_token_hash = None
        user.refresh_token_expires_at = None
        await self._commit_and_refresh(user)

        if token:
            await invalidate_current_user_cache(token)

    async def refresh_tokens(self, refresh_request: RefreshTokenRequest) -> TokenResponse:
        """Rotate a valid refresh token and return a new token pair."""

        try:
            email = decode_refresh_token(refresh_request.refresh_token)
        except JWTError:
            raise InvalidCredentialsError("Invalid or expired refresh token")

        user = await self.repository.get_user_by_email(email)
        if user is None:
            raise InvalidCredentialsError("Invalid or expired refresh token")

        stored_hash = user.refresh_token_hash
        expires_at = user.refresh_token_expires_at
        if (
            not stored_hash
            or not expires_at
            or _ensure_aware(expires_at) <= datetime.now(UTC)
            or stored_hash != hash_token(refresh_request.refresh_token)
        ):
            raise InvalidCredentialsError("Invalid or expired refresh token")

        token_pair = self._build_token_pair(subject=user.email, old_refresh_token=refresh_request.refresh_token)
        user.refresh_token_hash = hash_token(token_pair.refresh_token)
        user.refresh_token_expires_at = datetime.now(UTC) + timedelta(
            days=get_settings().refresh_token_expire_days
        )
        await self._commit_and_refresh(user)
        await cache_current_user(token_pair.access_token, user)
        return token_pair

    async def request_password_reset(self, reset_request: PasswordResetRequest, host: str) -> dict:
        """Generate a password reset token and send it via email."""

        user = await self.repository.get_user_by_email(reset_request.email)
        if user is None:
            # Do not expose that user doesn't exist
            return {"detail": "If the email exists, a password reset link has been sent"}

        reset_token = create_password_reset_token(user.email)
        settings = get_settings()
        host = host.rstrip("/")
        reset_path = f"{settings.api_v1_prefix}/auth/reset-password?token={reset_token}"
        reset_link = f"{host}{reset_path}"

        template_data = {"link": reset_link, "app_name": settings.app_name }
        user.password_reset_token_hash = hash_token(reset_token)
        user.password_reset_token_expires_at = datetime.now(UTC) + timedelta(
            minutes=settings.password_reset_token_expire_minutes
        )
        await self._commit_and_refresh(user)
        await send_verification_email_async(
            user.email, "Reset your password", template_data, template_name="password_reset.html"
        )
        return {"detail": "If the email exists, a password reset link has been sent"}

    async def reset_password(self, reset_update: PasswordResetUpdate) -> dict:
        """Verify password reset token and update password."""

        try:
            email = decode_password_reset_token(reset_update.token)
        except JWTError:
            raise InvalidCredentialsError("Invalid or expired password reset token")

        user = await self.repository.get_user_by_email(email)
        if user is None:
            raise InvalidCredentialsError("Invalid or expired password reset token")

        stored_hash = user.password_reset_token_hash
        expires_at = user.password_reset_token_expires_at
        if (
            not stored_hash
            or not expires_at
            or _ensure_aware(expires_at) <= datetime.now(UTC)
            or stored_hash != hash_token(reset_update.token)
        ):
            raise InvalidCredentialsError("Invalid or expired password reset token")

        user.hashed_password = hash_password(reset_update.password)
        user.password_reset_token_hash = None
        user.password_reset_token_expires_at = None
        await self._commit_and_refresh(user)
        return {"detail": "Password has been reset successfully"}
