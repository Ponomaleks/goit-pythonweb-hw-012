from __future__ import annotations

from datetime import UTC, date, datetime
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.contact import Contact
from app.models.user import User, UserRole
from app.api.v1.endpoints import users as users_module
from app.services.auth import create_email_verification_token, hash_password
from app.services import avatar as avatar_module
from app.services import auth as auth_module
from app.db.session import sessionmanager

pytestmark = pytest.mark.asyncio


async def create_user(
    email: str,
    password: str,
    *,
    role: UserRole = UserRole.USER,
    is_verified: bool = True,
) -> User:
    async with sessionmanager.session() as session:
        user = User(
            email=email,
            role=role,
            hashed_password=hash_password(password),
            is_active=True,
            is_verified=is_verified,
            avatar_url=None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


async def create_contact(user_id: int, **overrides) -> Contact:
    payload = {
        "first_name": "Jane",
        "last_name": "Doe",
        "email": "jane@example.com",
        "phone_number": "+380501112233",
        "birthday": date(1991, 2, 2),
        "additional_data": {"note": "integration"},
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
    }
    payload.update(overrides)

    async with sessionmanager.session() as session:
        contact = Contact(user_id=user_id, **payload)
        session.add(contact)
        await session.commit()
        await session.refresh(contact)
        return contact


async def login(client: AsyncClient, email: str, password: str) -> dict[str, str]:
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["access_token"]
    assert payload["refresh_token"]
    return payload


async def auth_headers(client: AsyncClient, email: str, password: str) -> dict[str, str]:
    payload = await login(client, email, password)
    return {"Authorization": f"Bearer {payload['access_token']}"}


async def test_auth_signup_verify_login_refresh_and_logout(
    client: AsyncClient, monkeypatch
) -> None:
    monkeypatch.setattr(auth_module, "send_verification_email_async", AsyncMock())

    signup_response = await client.post(
        "/api/v1/auth/signup",
        json={"email": "user@example.com", "password": "password123"},
    )
    assert signup_response.status_code == 201
    assert signup_response.json()["role"] == UserRole.USER.value

    verify_token = create_email_verification_token("user@example.com")
    verify_response = await client.get(
        "/api/v1/auth/verify",
        params={"token": verify_token},
    )
    assert verify_response.status_code == 200
    assert verify_response.json()["is_verified"] is True

    login_response = await client.post(
        "/api/v1/auth/login",
        data={"username": "user@example.com", "password": "password123"},
    )
    assert login_response.status_code == 200
    tokens = login_response.json()
    assert tokens["access_token"]
    assert tokens["refresh_token"]

    refresh_response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert refresh_response.status_code == 200
    assert refresh_response.json()["access_token"]

    logout_response = await client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert logout_response.status_code == 204


async def test_contacts_crud_flow(client: AsyncClient, monkeypatch) -> None:
    monkeypatch.setattr(auth_module, "send_verification_email_async", AsyncMock())

    await client.post(
        "/api/v1/auth/signup",
        json={"email": "contact-user@example.com", "password": "password123"},
    )
    await client.get(
        "/api/v1/auth/verify",
        params={"token": create_email_verification_token("contact-user@example.com")},
    )
    headers = await auth_headers(client, "contact-user@example.com", "password123")

    create_payload = {
        "first_name": "Jane",
        "last_name": "Doe",
        "email": "jane@example.com",
        "phone_number": "+380501112233",
        "birthday": "1991-02-02",
        "additional_data": {"note": "integration"},
    }
    create_response = await client.post(
        "/api/v1/contacts",
        json=create_payload,
        headers=headers,
    )
    assert create_response.status_code == 201
    contact_id = create_response.json()["id"]

    list_response = await client.get("/api/v1/contacts", headers=headers)
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1

    get_response = await client.get(f"/api/v1/contacts/{contact_id}", headers=headers)
    assert get_response.status_code == 200
    assert get_response.json()["email"] == "jane@example.com"

    put_response = await client.put(
        f"/api/v1/contacts/{contact_id}",
        json={
            "first_name": "Janet",
            "last_name": "Doe",
            "email": "janet@example.com",
            "phone_number": "+380501112244",
            "birthday": "1991-02-03",
            "additional_data": {"note": "updated"},
        },
        headers=headers,
    )
    assert put_response.status_code == 200
    assert put_response.json()["first_name"] == "Janet"

    patch_response = await client.patch(
        f"/api/v1/contacts/{contact_id}",
        json={"phone_number": "+380501112255"},
        headers=headers,
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["phone_number"] == "+380501112255"

    delete_response = await client.delete(f"/api/v1/contacts/{contact_id}", headers=headers)
    assert delete_response.status_code == 204


async def test_user_endpoints_and_avatar_update(client: AsyncClient, monkeypatch) -> None:
    monkeypatch.setattr(auth_module, "send_verification_email_async", AsyncMock())
    monkeypatch.setattr(users_module, "upload_avatar", AsyncMock(return_value="https://cdn.example.com/avatar.png"))

    await client.post(
        "/api/v1/auth/signup",
        json={"email": "profile-user@example.com", "password": "password123"},
    )
    await client.get(
        "/api/v1/auth/verify",
        params={"token": create_email_verification_token("profile-user@example.com")},
    )
    headers = await auth_headers(client, "profile-user@example.com", "password123")

    me_response = await client.get("/api/v1/users/me", headers=headers)
    assert me_response.status_code == 200
    assert me_response.json()["email"] == "profile-user@example.com"

    avatar_response = await client.patch(
        "/api/v1/users/me/avatar",
        headers=headers,
        files={"file": ("avatar.png", b"fake-image-bytes", "image/png")},
    )
    assert avatar_response.status_code == 200
    assert avatar_response.json()["avatar_url"] == "https://cdn.example.com/avatar.png"


async def test_rbac_restrictions_for_admin_and_moderator_routes(
    client: AsyncClient, monkeypatch
) -> None:
    monkeypatch.setattr(auth_module, "send_verification_email_async", AsyncMock())

    normal_user = await create_user("normal@example.com", "password123", role=UserRole.USER)
    moderator_user = await create_user("moderator@example.com", "password123", role=UserRole.MODERATOR)
    admin_user = await create_user("admin@example.com", "password123", role=UserRole.ADMIN)

    normal_headers = await auth_headers(client, "normal@example.com", "password123")
    moderator_headers = await auth_headers(client, "moderator@example.com", "password123")
    admin_headers = await auth_headers(client, "admin@example.com", "password123")

    normal_access_response = await client.get(
        "/api/v1/users/access-check",
        headers=normal_headers,
    )
    assert normal_access_response.status_code == 403

    forbidden_response = await client.patch(
        f"/api/v1/users/{normal_user.id}/role",
        json={"role": UserRole.MODERATOR.value},
        headers=normal_headers,
    )
    assert forbidden_response.status_code == 403

    role_update_response = await client.patch(
        f"/api/v1/users/{normal_user.id}/role",
        json={"role": UserRole.MODERATOR.value},
        headers=admin_headers,
    )
    assert role_update_response.status_code == 200
    assert role_update_response.json()["role"] == UserRole.MODERATOR.value

    moderator_access_response = await client.get(
        "/api/v1/users/access-check",
        headers=moderator_headers,
    )
    assert moderator_access_response.status_code == 200
    assert "Successful access" in moderator_access_response.json()["detail"]
