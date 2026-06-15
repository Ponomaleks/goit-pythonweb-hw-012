"""API-level dependencies shared across routers."""

from collections.abc import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.dependencies import get_db
from app.exceptions import InvalidTokenError, UserNotFoundError
from app.models.user import User, UserRole
from app.repositories.user import UserRepository
from app.services.auth import decode_access_token
from app.core.redis import cache_current_user, get_cached_current_user

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

    cached_user = await get_cached_current_user(token)
    if cached_user is not None:
        return cached_user

    user = await UserRepository(session).get_user_by_email(email)
    if user is None:
        raise UserNotFoundError("Authenticated user not found")

    await cache_current_user(token, user)
    return user


def require_roles(*allowed_roles: UserRole) -> Callable:
    """Build a dependency that allows only users with the given roles."""

    async def _role_guard(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user

    return _role_guard


require_admin = require_roles(UserRole.ADMIN)
require_moderator_or_admin = require_roles(UserRole.MODERATOR, UserRole.ADMIN)
