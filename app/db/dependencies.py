"""Yield a database session for request-scoped dependencies."""

from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import sessionmanager


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield a database session for request-scoped dependencies."""
    async with sessionmanager.session() as session:
        yield session
