"""Database access layer for users."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


class UserRepository:
    """Database access layer for users."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_user(
        self,
        email: str,
        hashed_password: str,
        avatar_url: str | None = None,
    ) -> User:
        """Create a user ORM object, add to session, and flush."""

        user = User(
            email=email,
            hashed_password=hashed_password,
            avatar_url=avatar_url,
        )
        self.session.add(user)
        await self.session.flush()
        return user

    async def get_user_by_id(self, user_id: int) -> User | None:
        """Return a user by primary key or `None` if it does not exist."""

        return await self.session.get(User, user_id)

    async def get_user_by_email(self, email: str) -> User | None:
        """Return a user by email or `None` if it does not exist."""

        stmt = select(User).where(User.email == email)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def mark_user_verified(self, user_id: int) -> User | None:
        """Mark a user as verified and return the updated user or `None`."""

        user = await self.get_user_by_id(user_id)
        if user is None:
            return None
        user.is_verified = True
        self.session.add(user)
        await self.session.flush()
        return user

    async def update_avatar_url(self, user_id: int, avatar_url: str) -> User | None:
        """Update a user's avatar URL and return the updated user or `None`."""

        user = await self.get_user_by_id(user_id)
        if user is None:
            return None
        user.avatar_url = avatar_url
        self.session.add(user)
        await self.session.flush()
        return user
