"""Redis client helpers for optional cache integration."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from functools import lru_cache

from redis.asyncio import Redis

from app.config import get_settings
from app.models.user import User, UserRole


@lru_cache(maxsize=1)
def get_redis_url() -> str | None:
    """Return the configured Redis URL, if any."""

    settings = get_settings()
    return settings.redis_url or settings.rate_limit_storage_url


@lru_cache(maxsize=1)
def get_redis_client() -> Redis | None:
    """Return a shared Redis client when Redis is configured and available."""

    redis_url = get_redis_url()
    if not redis_url:
        print("No Redis URL configured, skipping Redis client creation")
        return None

    try:
        print(f"Creating Redis client with URL: {redis_url}")
        return Redis.from_url(redis_url, decode_responses=True)
    except Exception:
        return None


def current_user_cache_key(token: str) -> str:
    """Build a cache key for the authenticated user session."""

    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    return f"auth:current-user:{token_hash}"


def _serialize_user(user: User) -> dict[str, str | int | bool | None]:
    """Serialize a user ORM object for cache storage."""

    return {
        "id": user.id,
        "email": user.email,
        "role": user.role.value if hasattr(user.role, "value") else str(user.role),
        "hashed_password": user.hashed_password,
        "is_active": user.is_active,
        "is_verified": user.is_verified,
        "avatar_url": user.avatar_url,
        "refresh_token_hash": user.refresh_token_hash,
        "refresh_token_expires_at": (
            user.refresh_token_expires_at.isoformat()
            if user.refresh_token_expires_at
            else None
        ),
        "password_reset_token_hash": user.password_reset_token_hash,
        "password_reset_token_expires_at": (
            user.password_reset_token_expires_at.isoformat()
            if user.password_reset_token_expires_at
            else None
        ),
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "updated_at": user.updated_at.isoformat() if user.updated_at else None,
    }


def _deserialize_user(payload: dict[str, object]) -> User:
    """Reconstruct a user ORM object from cached payload data."""

    return User(
        id=int(payload["id"]),
        email=str(payload["email"]),
        role=UserRole(str(payload["role"])),
        hashed_password=str(payload["hashed_password"]),
        is_active=bool(payload["is_active"]),
        is_verified=bool(payload["is_verified"]),
        avatar_url=payload.get("avatar_url") or None,
        refresh_token_hash=payload.get("refresh_token_hash") or None,
        refresh_token_expires_at=(
            datetime.fromisoformat(payload["refresh_token_expires_at"])
            if payload.get("refresh_token_expires_at")
            else None
        ),
        password_reset_token_hash=payload.get("password_reset_token_hash") or None,
        password_reset_token_expires_at=(
            datetime.fromisoformat(payload["password_reset_token_expires_at"])
            if payload.get("password_reset_token_expires_at")
            else None
        ),
        created_at=(
            datetime.fromisoformat(payload["created_at"])
            if payload.get("created_at")
            else datetime.now(UTC)
        ),
        updated_at=(
            datetime.fromisoformat(payload["updated_at"])
            if payload.get("updated_at")
            else datetime.now(UTC)
        ),
    )


async def cache_current_user(token: str, user: User) -> None:
    """Cache the authenticated user for a short period."""

    print(f"Caching user {user.email} for token: {token}")
    redis_client = get_redis_client()
    if redis_client is None:
        print("No Redis client available, skipping cache")
        return

    try:
        ttl_seconds = get_settings().current_user_cache_ttl_minutes * 60
        await redis_client.set(
            current_user_cache_key(token),
            json.dumps(_serialize_user(user)),
            ex=ttl_seconds,
        )
    except Exception:
        return


async def get_cached_current_user(token: str) -> User | None:
    """Return a cached authenticated user if present."""

    redis_client = get_redis_client()
    if redis_client is None:
        return None

    try:
        cached_user = await redis_client.get(current_user_cache_key(token))
        print(f"Retrieved cached user for token: {token}: {cached_user}")
    except Exception:
        return None

    if not cached_user:
        print(f"No cached user found for token: {token}")
        return None

    try:
        payload = json.loads(cached_user)
    except json.JSONDecodeError:
        return None

    if not isinstance(payload, dict):
        return None

    return _deserialize_user(payload)


async def invalidate_current_user_cache(token: str) -> None:
    """Remove the cached authenticated user session."""

    redis_client = get_redis_client()
    if redis_client is None:
        return

    try:
        await redis_client.delete(current_user_cache_key(token))
    except Exception:
        return
