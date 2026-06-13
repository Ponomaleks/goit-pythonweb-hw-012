"""Business logic for authentication operations."""

import bcrypt

from datetime import UTC, datetime, timedelta
from jose import jwt
from jose.exceptions import JWTError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.exceptions import (
    InvalidCredentialsError,
    UserAlreadyExistsError,
    UserNotFoundError,
)
from app.repositories.user import UserRepository
from app.schemas.user import TokenResponse, UserCreate, UserLogin, UserResponse
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


def create_access_token(subject: str) -> str:
    """Create a signed JWT access token for the given subject."""

    settings = get_settings()
    expire = datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(
        payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )


def create_email_verification_token(subject: str) -> str:
    """Create a time-limited token used for email verification."""

    settings = get_settings()
    expire = datetime.now(UTC) + timedelta(
        hours=settings.email_verification_token_expire_hours
    )
    payload = {"sub": subject, "exp": expire, "type": "email_verification"}
    return jwt.encode(
        payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
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


def decode_access_token(token: str) -> str:
    """Decode and validate a JWT access token, returning the subject."""

    settings = get_settings()
    payload = jwt.decode(
        token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
    )
    subject = payload.get("sub")
    if not subject or not isinstance(subject, str):
        raise InvalidCredentialsError("Invalid access token")
    return subject


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
        """Validate user credentials and return an access token."""

        user = await self.repository.get_user_by_email(user_in.email)
        if user is None or not verify_password(user_in.password, user.hashed_password):
            raise InvalidCredentialsError("Invalid email or password")
        if not user.is_verified:
            raise InvalidCredentialsError("Email address is not verified")

        access_token = create_access_token(subject=user.email)
        return TokenResponse(access_token=access_token)
