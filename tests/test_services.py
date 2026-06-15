from __future__ import annotations

import io
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.models.user import UserRole
from app.schemas.user import PasswordResetRequest, PasswordResetUpdate, UserCreate, UserLogin
from app.services import auth as auth_module
from app.services.auth import AuthService, hash_password, hash_token, verify_password
from app.services import avatar as avatar_module
from app.services import mailer as mailer_module


pytestmark = pytest.mark.asyncio


def make_settings() -> SimpleNamespace:
    return SimpleNamespace(
        jwt_secret_key="test-secret",
        jwt_algorithm="HS256",
        access_token_expire_minutes=60,
        refresh_token_expire_days=7,
        email_verification_token_expire_hours=48,
        password_reset_token_expire_minutes=30,
        api_v1_prefix="/api/v1",
        app_name="contacts-api",
        mail_username="mailer-user",
        mail_password="mailer-pass",
        mail_from="noreply@example.com",
        mail_port=2525,
        mail_server="smtp.example.com",
        mail_start_tls=True,
        mail_ssl_tls=False,
        email_from="noreply@example.com",
        smtp_host="localhost",
        smtp_port=1025,
        smtp_user=None,
        smtp_password=None,
        cloudinary_cloud_name="cloud",
        cloudinary_api_key="key",
        cloudinary_api_secret="secret",
        redis_url=None,
        rate_limit_storage_url=None,
        current_user_cache_ttl_minutes=15,
    )


def make_session() -> MagicMock:
    session = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.rollback = AsyncMock()
    return session


def make_user(**overrides) -> SimpleNamespace:
    data = {
        "id": 1,
        "email": "user@example.com",
        "role": UserRole.USER,
        "hashed_password": hash_password("password123"),
        "is_active": True,
        "is_verified": True,
        "avatar_url": None,
        "refresh_token_hash": None,
        "refresh_token_expires_at": None,
        "password_reset_token_hash": None,
        "password_reset_token_expires_at": None,
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
    }
    data.update(overrides)
    return SimpleNamespace(**data)


async def test_auth_register_user_hashes_password_and_sets_avatar(monkeypatch) -> None:
    session = make_session()
    service = AuthService(session)
    user = make_user(is_verified=False)

    repo = MagicMock()
    repo.get_user_by_email = AsyncMock(return_value=None)
    repo.create_user = AsyncMock(return_value=user)
    service.repository = repo
    service._commit_and_refresh = AsyncMock()

    monkeypatch.setattr(auth_module, "build_gravatar_url", lambda email: "avatar-url")
    monkeypatch.setattr(auth_module, "hash_password", lambda password: "hashed-password")

    result = await service.register_user(
        UserCreate(email="user@example.com", password="password123")
    )

    assert result.email == "user@example.com"
    repo.create_user.assert_awaited_once_with(
        email="user@example.com",
        hashed_password="hashed-password",
        avatar_url="avatar-url",
    )
    service._commit_and_refresh.assert_awaited_once_with(user)


async def test_auth_login_user_returns_token_pair_and_caches_user(monkeypatch) -> None:
    session = make_session()
    service = AuthService(session)
    user = make_user()

    repo = MagicMock()
    repo.get_user_by_email = AsyncMock(return_value=user)
    service.repository = repo
    service._commit_and_refresh = AsyncMock()

    cache_mock = AsyncMock()
    monkeypatch.setattr(auth_module, "cache_current_user", cache_mock)

    result = await service.login_user(
        UserLogin(email="user@example.com", password="password123")
    )

    assert result.access_token
    assert result.refresh_token
    cache_mock.assert_awaited_once_with(result.access_token, user)
    assert user.refresh_token_hash == hash_token(result.refresh_token)


async def test_auth_verify_email_marks_user_verified(monkeypatch) -> None:
    session = make_session()
    service = AuthService(session)
    user = make_user(is_verified=False)

    repo = MagicMock()
    repo.get_user_by_email = AsyncMock(return_value=user)
    service.repository = repo
    service._commit_and_refresh = AsyncMock()
    monkeypatch.setattr(auth_module, "decode_email_verification_token", lambda token: user.email)

    result = await service.verify_email("verification-token")

    assert result.is_verified is True
    service._commit_and_refresh.assert_awaited_once_with(user)


async def test_auth_refresh_tokens_rotates_refresh_token(monkeypatch) -> None:
    session = make_session()
    service = AuthService(session)
    refresh_token = "refresh-token"
    user = make_user(
        refresh_token_hash=hash_token(refresh_token),
        refresh_token_expires_at=datetime.now(UTC) + timedelta(days=1),
    )

    repo = MagicMock()
    repo.get_user_by_email = AsyncMock(return_value=user)
    service.repository = repo
    service._commit_and_refresh = AsyncMock()

    cache_mock = AsyncMock()
    monkeypatch.setattr(auth_module, "cache_current_user", cache_mock)
    monkeypatch.setattr(auth_module, "decode_refresh_token", lambda token: user.email)

    result = await service.refresh_tokens(
        auth_module.RefreshTokenRequest(refresh_token=refresh_token)
    )

    assert result.access_token
    assert result.refresh_token == refresh_token
    cache_mock.assert_awaited_once_with(result.access_token, user)
    assert user.refresh_token_hash == hash_token(refresh_token)


async def test_auth_logout_user_clears_refresh_token_and_cache(monkeypatch) -> None:
    session = make_session()
    service = AuthService(session)
    user = make_user(
        refresh_token_hash="stored",
        refresh_token_expires_at=datetime.now(UTC) + timedelta(days=1),
    )

    service._commit_and_refresh = AsyncMock()
    invalidate_mock = AsyncMock()
    monkeypatch.setattr(auth_module, "invalidate_current_user_cache", invalidate_mock)

    await service.logout_user(user, token="access-token")

    assert user.refresh_token_hash is None
    assert user.refresh_token_expires_at is None
    invalidate_mock.assert_awaited_once_with("access-token")


async def test_auth_request_password_reset_sends_email(monkeypatch) -> None:
    session = make_session()
    service = AuthService(session)
    user = make_user()

    repo = MagicMock()
    repo.get_user_by_email = AsyncMock(return_value=user)
    service.repository = repo
    service._commit_and_refresh = AsyncMock()

    send_mock = AsyncMock()
    monkeypatch.setattr(auth_module, "send_verification_email_async", send_mock)

    result = await service.request_password_reset(
        PasswordResetRequest(email="user@example.com"),
        host="http://testserver/",
    )

    assert result == {"detail": "If the email exists, a password reset link has been sent"}
    assert user.password_reset_token_hash
    send_mock.assert_awaited_once()


async def test_auth_reset_password_updates_password(monkeypatch) -> None:
    session = make_session()
    service = AuthService(session)
    reset_token = "reset-token"
    user = make_user(
        password_reset_token_hash=hash_token(reset_token),
        password_reset_token_expires_at=datetime.now(UTC) + timedelta(minutes=10),
    )

    repo = MagicMock()
    repo.get_user_by_email = AsyncMock(return_value=user)
    service.repository = repo
    service._commit_and_refresh = AsyncMock()
    monkeypatch.setattr(auth_module, "decode_password_reset_token", lambda token: user.email)

    result = await service.reset_password(
        PasswordResetUpdate(token=reset_token, password="newpassword123")
    )

    assert result == {"detail": "Password has been reset successfully"}
    assert verify_password("newpassword123", user.hashed_password)
    assert user.password_reset_token_hash is None
    assert user.password_reset_token_expires_at is None


async def test_mailer_get_mail_config_uses_settings(monkeypatch) -> None:
    settings = make_settings()
    monkeypatch.setattr(mailer_module, "get_settings", lambda: settings)

    config = mailer_module.get_mail_config()

    assert config.MAIL_SERVER == settings.mail_server
    assert config.MAIL_PORT == settings.mail_port
    assert config.MAIL_USERNAME == settings.mail_username


async def test_mailer_send_verification_email_uses_fastmail(monkeypatch) -> None:
    settings = make_settings()
    monkeypatch.setattr(mailer_module, "get_settings", lambda: settings)

    sent = {}

    class FakeFastMail:
        def __init__(self, conf):
            sent["conf"] = conf

        async def send_message(self, message, template_name=None):
            sent["message"] = message
            sent["template_name"] = template_name

    class FakeMessageSchema:
        def __init__(self, subject, recipients, template_body, subtype):
            self.subject = subject
            self.recipients = recipients
            self.template_body = template_body
            self.subtype = subtype

    monkeypatch.setattr(mailer_module, "FastMail", FakeFastMail)
    monkeypatch.setattr(mailer_module, "MessageSchema", FakeMessageSchema)

    await mailer_module.send_verification_email(
        "user@example.com",
        "Verify your email",
        {"link": "http://example.com", "app_name": "contacts-api"},
    )

    assert sent["template_name"] == "verification.html"
    assert sent["message"].subject == "Verify your email"


async def test_avatar_build_gravatar_url_is_deterministic() -> None:
    first = avatar_module.build_gravatar_url("User@example.com")
    second = avatar_module.build_gravatar_url(" user@example.com ")

    assert first == second
    assert first.startswith("https://www.gravatar.com/avatar/")


async def test_avatar_upload_rejects_non_image(monkeypatch) -> None:
    settings = make_settings()
    monkeypatch.setattr(avatar_module, "get_settings", lambda: settings)

    file = SimpleNamespace(content_type="text/plain", file=io.BytesIO(b"data"))

    with pytest.raises(HTTPException) as exc_info:
        await avatar_module.upload_avatar(file, user_id=1)

    assert exc_info.value.status_code == 400


async def test_avatar_upload_returns_secure_url(monkeypatch) -> None:
    settings = make_settings()
    monkeypatch.setattr(avatar_module, "get_settings", lambda: settings)
    monkeypatch.setattr(avatar_module, "_configure_cloudinary", lambda: None)
    monkeypatch.setattr(
        avatar_module.cloudinary.uploader,
        "upload",
        lambda *args, **kwargs: {"secure_url": "https://cdn.example.com/avatar.png"},
    )

    file = SimpleNamespace(content_type="image/png", file=io.BytesIO(b"image-bytes"))

    url = await avatar_module.upload_avatar(file, user_id=7)

    assert url == "https://cdn.example.com/avatar.png"
