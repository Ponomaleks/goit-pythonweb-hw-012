"""Business logic for contacts operations."""

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import ContactAlreadyExistsError, ContactNotFoundError
from app.repositories.contact import ContactRepository
from app.schemas.contact import (
    ContactCreate,
    ContactResponse,
    ContactSearchQuery,
    ContactUpdate,
    UpcomingBirthdayResponse,
)


class ContactService:
    """Business logic for contacts operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.repository = ContactRepository(session)
        self.session = session

    async def _commit_and_refresh(self, contact) -> None:
        """Commit the transaction and refresh the contact instance.

        Args:
            contact: ORM contact instance to refresh after commit.
        """
        try:
            await self.session.commit()
            await self.session.refresh(contact)
        except IntegrityError as exc:
            await self.session.rollback()
            raise ContactAlreadyExistsError(
                "Contact with this email already exists"
            ) from exc

    async def _get_by_id_or_raise(self, user_id: int, contact_id: int):
        """Fetch a contact by ID or raise an error.

        Args:
            user_id: Owning user identifier.
            contact_id: Contact identifier.

        Returns:
            Contact ORM instance.
        """
        contact = await self.repository.get_contact_by_id(contact_id, user_id)
        if not contact:
            raise ContactNotFoundError(f"Contact with id {contact_id} not found")
        return contact

    async def _ensure_email_is_available(
        self,
        user_id: int,
        email: str,
        *,
        exclude_contact_id: int | None = None,
    ) -> None:
        """Raise if another contact already uses the given email."""

        existing_contact = await self.repository.get_contact_by_email(email, user_id)
        if existing_contact and existing_contact.id != exclude_contact_id:
            raise ContactAlreadyExistsError("Contact with this email already exists")

    async def create_contact(
        self, user_id: int, contact_in: ContactCreate
    ) -> ContactResponse:
        """Validate and create a new contact.

        Args:
            user_id: Owning user identifier.
            contact_in: Contact creation payload.

        Returns:
            Created contact response model.
        """

        try:
            await self._ensure_email_is_available(user_id, contact_in.email)
            contact = await self.repository.create_contact(contact_in, user_id)
            await self._commit_and_refresh(contact)
        except IntegrityError as exc:
            await self.session.rollback()
            raise ContactAlreadyExistsError(
                "Contact with this email already exists"
            ) from exc
        return ContactResponse.model_validate(contact)

    async def get_contact(self, user_id: int, contact_id: int) -> ContactResponse:
        """Return a single contact or raise a not-found error.

        Args:
            user_id: Owning user identifier.
            contact_id: Contact identifier.

        Returns:
            Contact response model.
        """

        contact = await self._get_by_id_or_raise(user_id, contact_id)
        return ContactResponse.model_validate(contact)

    async def list_contacts(
        self, user_id: int, skip: int = 0, limit: int = 10
    ) -> list[ContactResponse]:
        """Return the current contacts collection with pagination.

        Args:
            user_id: Owning user identifier.
            skip: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            List of contact response models.
        """

        contacts = await self.repository.get_contacts_list(user_id, skip, limit)
        return [ContactResponse.model_validate(contact) for contact in contacts]

    async def search_contacts(
        self, user_id: int, query: ContactSearchQuery
    ) -> list[ContactResponse]:
        """Return contacts matching the requested query parameters.

        Args:
            user_id: Owning user identifier.
            query: Search criteria.

        Returns:
            List of contact response models.
        """

        contacts = await self.repository.search_contact(user_id, query)
        return [ContactResponse.model_validate(contact) for contact in contacts]

    async def update_contact(
        self, user_id: int, contact_id: int, contact_in: ContactCreate
    ) -> ContactResponse:
        """Replace an existing contact using a complete payload.

        Args:
            user_id: Owning user identifier.
            contact_id: Contact identifier.
            contact_in: Complete contact payload.

        Returns:
            Updated contact response model.
        """

        contact = await self._get_by_id_or_raise(user_id, contact_id)
        try:
            await self._ensure_email_is_available(
                user_id, contact_in.email, exclude_contact_id=contact_id
            )
            contact = await self.repository.replace_contact(contact, contact_in)
            await self._commit_and_refresh(contact)
        except IntegrityError as exc:
            await self.session.rollback()
            raise ContactAlreadyExistsError(
                "Contact with this email already exists"
            ) from exc
        return ContactResponse.model_validate(contact)

    async def patch_contact(
        self, user_id: int, contact_id: int, contact_in: ContactUpdate
    ) -> ContactResponse:
        """Partially update an existing contact.

        Args:
            user_id: Owning user identifier.
            contact_id: Contact identifier.
            contact_in: Partial contact payload.

        Returns:
            Updated contact response model.
        """

        contact = await self._get_by_id_or_raise(user_id, contact_id)
        try:
            update_data = contact_in.model_dump(exclude_unset=True)
            email = update_data.get("email")
            if email is not None:
                await self._ensure_email_is_available(
                    user_id, email, exclude_contact_id=contact_id
                )
            contact = await self.repository.patch_contact(contact, contact_in)
            await self._commit_and_refresh(contact)
        except IntegrityError as exc:
            await self.session.rollback()
            raise ContactAlreadyExistsError(
                "Contact with this email already exists"
            ) from exc
        return ContactResponse.model_validate(contact)

    async def delete_contact(self, user_id: int, contact_id: int) -> None:
        """Delete an existing contact or raise a not-found error.

        Args:
            user_id: Owning user identifier.
            contact_id: Contact identifier.
        """

        contact = await self._get_by_id_or_raise(user_id, contact_id)
        await self.repository.delete_contact(contact)
        await self.session.commit()

    async def get_upcoming_birthdays(
        self, user_id: int, days: int = 7
    ) -> list[UpcomingBirthdayResponse]:
        """Return the contacts whose birthdays are within the next 7 days.

        Args:
            user_id: Owning user identifier.
            days: Look-ahead window in days.

        Returns:
            List of upcoming birthday response models.
        """

        contacts = await self.repository.get_upcoming_birthdays(user_id, days)
        return [
            UpcomingBirthdayResponse.model_validate(contact) for contact in contacts
        ]
