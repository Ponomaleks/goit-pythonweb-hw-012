"""HTTP endpoints for contacts resources."""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.db.dependencies import get_db
from app.models.user import User
from app.schemas.contact import (
    ContactCreate,
    ContactResponse,
    ContactSearchQuery,
    ContactUpdate,
    UpcomingBirthdayResponse,
)
from app.services.contact import ContactService

router = APIRouter(prefix="/contacts", tags=["contacts"])


@router.post(
    "",
    response_model=ContactResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new contact",
)
async def create_contact(
    contact_in: ContactCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ContactResponse:
    """Create a new contact with the provided data.

    Args:
        contact_in: Contact creation payload.
        current_user: Authenticated user.
        session: Active database session.

    Returns:
        Created contact response model.
    """
    service = ContactService(session)
    return await service.create_contact(current_user.id, contact_in)


@router.get(
    "",
    response_model=list[ContactResponse],
    status_code=status.HTTP_200_OK,
    summary="List all contacts",
)
async def list_contacts(
    skip: int = Query(0, ge=0, description="Number of contacts to skip"),
    limit: int = Query(10, ge=1, le=100, description="Number of contacts to return"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> list[ContactResponse]:
    """Return a paginated list of all contacts.

    Args:
        skip: Number of records to skip.
        limit: Maximum number of records to return.
        current_user: Authenticated user.
        session: Active database session.

    Returns:
        List of contact response models.
    """
    service = ContactService(session)
    return await service.list_contacts(current_user.id, skip, limit)


@router.get(
    "/search",
    response_model=list[ContactResponse],
    status_code=status.HTTP_200_OK,
    summary="Search contacts",
)
async def search_contacts(
    first_name: str | None = Query(None, min_length=1, max_length=100),
    last_name: str | None = Query(None, min_length=1, max_length=100),
    email: str | None = Query(None, min_length=1, max_length=255),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> list[ContactResponse]:
    """Search for contacts by first name, last name, or email.

    Args:
        first_name: Optional first-name filter.
        last_name: Optional last-name filter.
        email: Optional email filter.
        current_user: Authenticated user.
        session: Active database session.

    Returns:
        List of contact response models.
    """
    query = ContactSearchQuery(first_name=first_name, last_name=last_name, email=email)
    service = ContactService(session)
    return await service.search_contacts(current_user.id, query)


@router.get(
    "/birthdays/upcoming",
    response_model=list[UpcomingBirthdayResponse],
    status_code=status.HTTP_200_OK,
    summary="Get upcoming birthdays",
)
async def get_upcoming_birthdays(
    days: int = Query(7, ge=1, le=365, description="Number of days to look ahead"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> list[UpcomingBirthdayResponse]:
    """Return contacts whose birthdays fall within the next N days.

    Args:
        days: Look-ahead window in days.
        current_user: Authenticated user.
        session: Active database session.

    Returns:
        List of upcoming birthday response models.
    """
    service = ContactService(session)
    return await service.get_upcoming_birthdays(current_user.id, days)


@router.get(
    "/{contact_id}",
    response_model=ContactResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a contact by ID",
)
async def get_contact_by_id(
    contact_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ContactResponse:
    """Return a single contact by its ID.

    Args:
        contact_id: Contact identifier.
        current_user: Authenticated user.
        session: Active database session.

    Returns:
        Contact response model.
    """
    service = ContactService(session)
    return await service.get_contact(current_user.id, contact_id)


@router.put(
    "/{contact_id}",
    response_model=ContactResponse,
    status_code=status.HTTP_200_OK,
    summary="Replace a contact",
)
async def update_contact(
    contact_id: int,
    contact_in: ContactCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ContactResponse:
    """Replace an existing contact.

    Args:
        contact_id: Contact identifier.
        contact_in: Complete contact payload.
        current_user: Authenticated user.
        session: Active database session.

    Returns:
        Updated contact response model.
    """
    service = ContactService(session)
    return await service.update_contact(current_user.id, contact_id, contact_in)


@router.patch(
    "/{contact_id}",
    response_model=ContactResponse,
    status_code=status.HTTP_200_OK,
    summary="Partially update a contact",
)
async def patch_contact(
    contact_id: int,
    contact_in: ContactUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ContactResponse:
    """Partially update a contact with one or more fields.

    Args:
        contact_id: Contact identifier.
        contact_in: Partial contact payload.
        current_user: Authenticated user.
        session: Active database session.

    Returns:
        Updated contact response model.
    """
    service = ContactService(session)
    return await service.patch_contact(current_user.id, contact_id, contact_in)


@router.delete(
    "/{contact_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a contact",
)
async def delete_contact(
    contact_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> None:
    """Delete a contact by its ID.

    Args:
        contact_id: Contact identifier.
        current_user: Authenticated user.
        session: Active database session.
    """
    service = ContactService(session)
    await service.delete_contact(current_user.id, contact_id)
