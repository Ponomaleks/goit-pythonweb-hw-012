from __future__ import annotations

from datetime import UTC, date, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.contact import Contact
from app.models.user import User, UserRole
from app.repositories.contact import ContactRepository
from app.repositories.user import UserRepository
from app.schemas.contact import ContactCreate, ContactSearchQuery, ContactUpdate


pytestmark = pytest.mark.asyncio


def make_session() -> MagicMock:
    session = MagicMock()
    session.add = MagicMock()
    session.delete = AsyncMock()
    session.flush = AsyncMock()
    session.execute = AsyncMock()
    session.get = AsyncMock()
    return session


def make_user(**overrides) -> User:
    data = {
        "id": 1,
        "email": "user@example.com",
        "role": UserRole.USER,
        "hashed_password": "hashed-password",
        "is_active": True,
        "is_verified": False,
        "avatar_url": None,
        "refresh_token_hash": None,
        "refresh_token_expires_at": None,
        "password_reset_token_hash": None,
        "password_reset_token_expires_at": None,
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
    }
    data.update(overrides)
    return User(**data)


def make_contact(**overrides) -> Contact:
    data = {
        "id": 1,
        "user_id": 1,
        "first_name": "John",
        "last_name": "Doe",
        "email": "john@example.com",
        "phone_number": "+1234567890",
        "birthday": date(1990, 1, 1),
        "additional_data": None,
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
    }
    data.update(overrides)
    return Contact(**data)


def make_scalar_result(value):
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


def make_list_result(values):
    result = MagicMock()
    scalars_result = MagicMock()
    scalars_result.all.return_value = values
    result.scalars.return_value = scalars_result
    return result


async def test_user_repository_create_user_defaults_to_user_role() -> None:
    session = make_session()
    repository = UserRepository(session)

    user = await repository.create_user(
        email="user@example.com",
        hashed_password="hashed-password",
    )

    assert user.email == "user@example.com"
    assert user.role == UserRole.USER
    session.add.assert_called_once_with(user)
    session.flush.assert_awaited_once()


async def test_user_repository_get_user_by_email_returns_user() -> None:
    session = make_session()
    user = make_user()
    session.execute.return_value = make_scalar_result(user)
    repository = UserRepository(session)

    result = await repository.get_user_by_email("user@example.com")

    assert result is user
    session.execute.assert_awaited_once()


async def test_user_repository_update_user_role_updates_user() -> None:
    session = make_session()
    user = make_user(role=UserRole.USER)
    session.get.return_value = user
    repository = UserRepository(session)

    updated = await repository.update_user_role(user.id, UserRole.ADMIN)

    assert updated is user
    assert user.role == UserRole.ADMIN
    session.add.assert_called_once_with(user)
    session.flush.assert_awaited_once()


async def test_user_repository_mark_user_verified_updates_flag() -> None:
    session = make_session()
    user = make_user(is_verified=False)
    session.get.return_value = user
    repository = UserRepository(session)

    updated = await repository.mark_user_verified(user.id)

    assert updated is user
    assert user.is_verified is True
    session.add.assert_called_once_with(user)
    session.flush.assert_awaited_once()


async def test_user_repository_update_avatar_url_updates_value() -> None:
    session = make_session()
    user = make_user(avatar_url=None)
    session.get.return_value = user
    repository = UserRepository(session)

    updated = await repository.update_avatar_url(user.id, "https://avatar.example.com")

    assert updated is user
    assert user.avatar_url == "https://avatar.example.com"
    session.add.assert_called_once_with(user)
    session.flush.assert_awaited_once()


async def test_contact_repository_create_contact_adds_contact() -> None:
    session = make_session()
    repository = ContactRepository(session)
    contact_in = ContactCreate(
        first_name="Jane",
        last_name="Doe",
        email="jane@example.com",
        phone_number="+1234567890",
        birthday=date(1991, 2, 2),
    )

    contact = await repository.create_contact(contact_in, user_id=7)

    assert contact.user_id == 7
    assert contact.email == "jane@example.com"
    session.add.assert_called_once_with(contact)
    session.flush.assert_awaited_once()


async def test_contact_repository_get_contact_by_id_returns_contact() -> None:
    session = make_session()
    contact = make_contact()
    session.execute.return_value = make_scalar_result(contact)
    repository = ContactRepository(session)

    result = await repository.get_contact_by_id(contact.id, contact.user_id)

    assert result is contact
    session.execute.assert_awaited_once()


async def test_contact_repository_get_contact_by_email_returns_contact() -> None:
    session = make_session()
    contact = make_contact()
    session.execute.return_value = make_scalar_result(contact)
    repository = ContactRepository(session)

    result = await repository.get_contact_by_email(contact.email, contact.user_id)

    assert result is contact
    session.execute.assert_awaited_once()


async def test_contact_repository_get_contacts_list_clamps_pagination() -> None:
    session = make_session()
    contacts = [make_contact(id=1), make_contact(id=2)]
    session.execute.return_value = make_list_result(contacts)
    repository = ContactRepository(session)

    result = await repository.get_contacts_list(user_id=1, skip=-5, limit=500)

    assert result == contacts
    statement = session.execute.await_args.args[0]
    compiled = str(statement.compile(compile_kwargs={"literal_binds": True}))
    assert "LIMIT 100" in compiled
    assert "OFFSET 0" in compiled


async def test_contact_repository_search_contact_applies_filters() -> None:
    session = make_session()
    contacts = [make_contact()]
    session.execute.return_value = make_list_result(contacts)
    repository = ContactRepository(session)
    query = ContactSearchQuery(first_name="Jo", last_name=None, email=None)

    result = await repository.search_contact(user_id=1, query=query)

    assert result == contacts
    statement = session.execute.await_args.args[0]
    compiled = str(statement.compile(compile_kwargs={"literal_binds": True}))
    assert "like" in compiled.lower()


async def test_contact_repository_replace_contact_updates_fields() -> None:
    session = make_session()
    contact = make_contact()
    repository = ContactRepository(session)
    contact_in = ContactCreate(
        first_name="Updated",
        last_name="User",
        email="updated@example.com",
        phone_number="+1987654321",
        birthday=date(1992, 3, 3),
    )

    updated = await repository.replace_contact(contact, contact_in)

    assert updated.first_name == "Updated"
    assert updated.email == "updated@example.com"
    session.flush.assert_awaited_once()


async def test_contact_repository_patch_contact_updates_partial_fields() -> None:
    session = make_session()
    contact = make_contact()
    repository = ContactRepository(session)
    contact_in = ContactUpdate(first_name="Patched")

    updated = await repository.patch_contact(contact, contact_in)

    assert updated.first_name == "Patched"
    assert updated.email == contact.email
    session.flush.assert_awaited_once()


async def test_contact_repository_delete_contact_deletes_from_session() -> None:
    session = make_session()
    contact = make_contact()
    repository = ContactRepository(session)

    await repository.delete_contact(contact)

    session.delete.assert_awaited_once_with(contact)
    session.flush.assert_awaited_once()
