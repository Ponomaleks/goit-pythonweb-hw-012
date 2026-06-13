"""Database access layer for contacts."""

from datetime import date, timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.contact import Contact
from app.schemas.contact import ContactCreate, ContactSearchQuery, ContactUpdate


class ContactRepository:
    """Database access layer for contacts."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_contact(self, contact_in: ContactCreate, user_id: int) -> Contact:
        """Create a Contact ORM object, add to session, and flush (sync without commit)."""

        contact = Contact(**contact_in.model_dump(), user_id=user_id)
        self.session.add(contact)
        await self.session.flush()
        return contact

    async def get_contact_by_id(self, contact_id: int, user_id: int) -> Contact | None:
        """Return a contact by primary key or `None` if it does not exist."""

        stmt = select(Contact).where(
            Contact.id == contact_id, Contact.user_id == user_id
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_contact_by_email(self, email: str, user_id: int) -> Contact | None:
        """Return a contact by email or `None` if it does not exist."""

        stmt = select(Contact).where(Contact.email == email, Contact.user_id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_contacts_list(
        self, user_id: int, skip: int = 0, limit: int = 10
    ) -> list[Contact]:
        """Return a paginated list of contacts ordered by creation time or name."""

        # Apply pagination constraints: skip >= 0, 1 <= limit <= 100
        skip = max(0, skip)
        limit = max(1, min(limit, 100))

        stmt = (
            select(Contact)
            .where(Contact.user_id == user_id)
            .offset(skip)
            .limit(limit)
            .order_by(Contact.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def search_contact(
        self, user_id: int, query: ContactSearchQuery
    ) -> list[Contact]:
        """Return contacts filtered by first name, last name, or email (OR logic)."""

        filters = []
        if query.first_name:
            filters.append(Contact.first_name.ilike(f"%{query.first_name}%"))
        if query.last_name:
            filters.append(Contact.last_name.ilike(f"%{query.last_name}%"))
        if query.email:
            filters.append(Contact.email.ilike(f"%{query.email}%"))

        stmt = select(Contact).where(Contact.user_id == user_id)
        if filters:
            # Use OR logic: match ANY filter, not ALL.
            stmt = stmt.where(or_(*filters))

        result = await self.session.execute(stmt.order_by(Contact.created_at.desc()))
        return list(result.scalars().all())

    async def replace_contact(
        self, contact: Contact, contact_in: ContactCreate
    ) -> Contact:
        """Replace all mutable contact fields using a complete payload."""

        for field, value in contact_in.model_dump().items():
            setattr(contact, field, value)

        await self.session.flush()
        return contact

    async def patch_contact(
        self, contact: Contact, contact_in: ContactUpdate
    ) -> Contact:
        """Apply partial updates to an existing contact."""

        update_data = contact_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(contact, field, value)

        await self.session.flush()
        return contact

    async def delete_contact(self, contact: Contact) -> None:
        """Remove a contact from session, and flush (sync without commit)."""

        await self.session.delete(contact)
        await self.session.flush()

    async def get_upcoming_birthdays(
        self, user_id: int, days: int = 7
    ) -> list[Contact]:
        """Return contacts whose birthday falls within the next N days."""

        today = date.today()
        end_date = today + timedelta(days=days)

        # Compare birthdays ignoring year by reducing both dates to MMDD integer.
        birthday_mmdd = (func.extract("month", Contact.birthday) * 100) + func.extract(
            "day", Contact.birthday
        )
        start_mmdd = today.month * 100 + today.day
        end_mmdd = end_date.month * 100 + end_date.day

        if start_mmdd <= end_mmdd:
            condition = birthday_mmdd.between(start_mmdd, end_mmdd)
        else:
            # Year boundary case, e.g. Dec -> Jan.
            condition = or_(birthday_mmdd >= start_mmdd, birthday_mmdd <= end_mmdd)

        stmt = (
            select(Contact)
            .where(Contact.user_id == user_id, condition)
            .order_by(Contact.birthday.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
