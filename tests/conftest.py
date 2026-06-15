from __future__ import annotations

import os
from pathlib import Path

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

# Force a dedicated async SQLite test database before importing the app.
TEST_DB_PATH = Path(__file__).resolve().parent / ".pytest_integration.db"
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{TEST_DB_PATH.as_posix()}"
os.environ["REDIS_URL"] = ""
os.environ["RATE_LIMIT_STORAGE_URL"] = ""

from app.db.base import Base
from app.db.session import sessionmanager
from app.main import app


@pytest_asyncio.fixture(scope="session", autouse=True)
async def prepare_test_database() -> None:
    """Create the test schema before the integration suite runs."""

    async with sessionmanager._engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with sessionmanager._engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client() -> AsyncClient:
    """Return an ASGI client bound to the FastAPI app."""

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as async_client:
        yield async_client
