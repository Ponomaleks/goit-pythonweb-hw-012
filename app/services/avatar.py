"""Utilities for user avatar uploads."""

from __future__ import annotations

import asyncio
import hashlib
from dataclasses import dataclass

import cloudinary
import cloudinary.uploader
from fastapi import HTTPException, UploadFile, status

from app.config import get_settings


@dataclass(frozen=True)
class CloudinaryConfig:
    cloud_name: str
    api_key: str
    api_secret: str


def build_gravatar_url(email: str, size: int = 200) -> str:
    """Return a deterministic Gravatar URL for the given email address."""

    normalized_email = email.strip().lower().encode("utf-8")
    email_hash = hashlib.md5(normalized_email, usedforsecurity=False).hexdigest()
    return "https://www.gravatar.com/avatar/" f"{email_hash}?s={size}&d=identicon&r=g"


def _get_cloudinary_config() -> CloudinaryConfig:
    settings = get_settings()
    cloud_name = settings.cloudinary_cloud_name
    api_key = settings.cloudinary_api_key
    api_secret = settings.cloudinary_api_secret

    if not (cloud_name and api_key and api_secret):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Cloudinary is not configured",
        )

    return CloudinaryConfig(
        cloud_name=cloud_name,
        api_key=api_key,
        api_secret=api_secret,
    )


def _configure_cloudinary() -> None:
    config = _get_cloudinary_config()
    cloudinary.config(
        cloud_name=config.cloud_name,
        api_key=config.api_key,
        api_secret=config.api_secret,
        secure=True,
    )


async def upload_avatar(file: UploadFile, user_id: int) -> str:
    """Upload an avatar image to Cloudinary and return its secure URL."""

    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Avatar must be an image",
        )

    _configure_cloudinary()
    file.file.seek(0)

    result = await asyncio.to_thread(
        cloudinary.uploader.upload,
        file.file,
        folder="contacts-api/avatars",
        public_id=f"user-{user_id}",
        overwrite=True,
        invalidate=True,
    )
    secure_url = result.get("secure_url")
    if not secure_url:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to upload avatar",
        )
    return secure_url
