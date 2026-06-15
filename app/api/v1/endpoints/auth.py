"""HTTP endpoints for authentication resources."""

from fastapi import APIRouter, Depends, status, BackgroundTasks, Request, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.dependencies import get_db
from app.api.dependencies import get_current_user, oauth2_scheme
from app.schemas.user import (
    EmailRequest,
    RefreshTokenRequest,
    TokenResponse,
    UserCreate,
    UserLogin,
    UserResponse,
    PasswordResetRequest,
    PasswordResetUpdate,
)
from app.services.auth import AuthService
router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/signup",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
async def signup(
    user_in: UserCreate,
    background_tasks: BackgroundTasks,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Create a new user account."""

    service = AuthService(session)
    created = await service.register_user(user_in)
    # Fetch ORM user entity to send verification in background
    user_entity = await service.repository.get_user_by_email(created.email)
    if user_entity is not None:
        background_tasks.add_task(
            service.send_verification_email, user_entity, str(request.base_url)
        )
    return created


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Authenticate a user",
)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Authenticate a user and return a token pair."""

    service = AuthService(session)
    user_in = UserLogin(email=form_data.username, password=form_data.password)
    return await service.login_user(user_in)

@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Logout the current user",
)
async def logout(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> None:
    """Invalidate the current user's refresh token."""

    if current_user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")

    service = AuthService(session)
    await service.logout_user(current_user, token=token)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Refresh an access token",
)
async def refresh(
    refresh_request: RefreshTokenRequest,
    session: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Rotate a refresh token and issue a new token pair."""

    service = AuthService(session)
    return await service.refresh_tokens(refresh_request)


@router.get("/verify", response_model=UserResponse, summary="Verify an email token")
async def verify_email(
    token: str, session: AsyncSession = Depends(get_db)
) -> UserResponse:
    """Verify an email confirmation token and mark the user as verified."""

    service = AuthService(session)
    return await service.verify_email(token)


@router.post("/resend-verification", summary="Resend verification email")
async def resend_verification(
    email_request: EmailRequest,
    background_tasks: BackgroundTasks,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Resend the verification email to the provided address (if the user exists)."""

    repo = AuthService(session).repository
    user = await repo.get_user_by_email(email_request.email)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if user.is_verified:
        return {"detail": "User already verified"}

    service = AuthService(session)
    # Send email in background so request returns quickly
    background_tasks.add_task(
        service.send_verification_email, user, host=str(request.base_url)
    )
    return {"detail": "Verification email queued"}


@router.post("/forgot-password", summary="Request a password reset")
async def forgot_password(
    reset_request: PasswordResetRequest,
    background_tasks: BackgroundTasks,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Request a password reset by email."""

    service = AuthService(session)
    background_tasks.add_task(
        service.request_password_reset, reset_request, str(request.base_url)
    )
    return {"detail": "If the email exists, a password reset link has been sent"}


@router.post("/reset-password", summary="Reset password with token")
async def reset_password(
    reset_update: PasswordResetUpdate,
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Reset password using a valid password reset token."""

    service = AuthService(session)
    return await service.reset_password(reset_update)
