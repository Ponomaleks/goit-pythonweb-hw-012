"""API-level dependencies shared across routers."""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.dependencies import get_db
from app.exceptions import InvalidTokenError, UserNotFoundError
from app.models.user import User
from app.repositories.user import UserRepository
from app.services.auth import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_db),
) -> User:
    """Return the current authenticated user from a bearer token."""

    try:
        email = decode_access_token(token)
    except Exception as exc:
        raise InvalidTokenError("Invalid access token") from exc

    user = await UserRepository(session).get_user_by_email(email)
    if user is None:
        raise UserNotFoundError("Authenticated user not found")
    return user
