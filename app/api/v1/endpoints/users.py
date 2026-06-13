"""HTTP endpoints for user resources."""

from fastapi import APIRouter, Depends, File, Request, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.db.dependencies import get_db
from app.config import get_settings
from app.core.limiter import limiter
from app.models.user import User
from app.schemas.user import UserResponse
from app.repositories.user import UserRepository
from app.services.avatar import upload_avatar

settings = get_settings()

router = APIRouter(prefix="/users", tags=["users"])


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get the current user",
)
@limiter.limit(settings.rate_limit_default)
async def get_current_user_profile(
    request: Request,
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """Return the authenticated user's profile."""

    return UserResponse.model_validate(current_user)


@router.patch(
    "/me/avatar",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Update the current user's avatar",
)
@limiter.limit(settings.rate_limit_default)
async def update_current_user_avatar(
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Upload a new avatar image for the authenticated user."""

    avatar_url = await upload_avatar(file, current_user.id)
    repository = UserRepository(session)
    updated_user = await repository.update_avatar_url(current_user.id, avatar_url)
    if updated_user is None:
        return UserResponse.model_validate(current_user)

    await session.commit()
    await session.refresh(updated_user)
    return UserResponse.model_validate(updated_user)
