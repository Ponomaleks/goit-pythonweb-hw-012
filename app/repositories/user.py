"""Database access layer for users."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.user import UserRole


class UserRepository:
    """Database access layer for users."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_user(
        self,
        email: str,
        hashed_password: str,
        role: UserRole = UserRole.USER,
        avatar_url: str | None = None,
    ) -> User:
        """Create a user ORM object, add it to the session, and flush.

        Args:
            email: User email address.
            hashed_password: Pre-hashed password.
            role: Assigned user role.
            avatar_url: Optional avatar URL.

        Returns:
            Created user ORM instance.
        """

        user = User(
            email=email,
            role=role,
            hashed_password=hashed_password,
            avatar_url=avatar_url,
        )
        self.session.add(user)
        await self.session.flush()
        return user

    async def update_user_role(self, user_id: int, role: UserRole) -> User | None:
        """Update a user's role.

        Args:
            user_id: User identifier.
            role: New role value.

        Returns:
            Updated user ORM instance or `None`.
        """

        user = await self.get_user_by_id(user_id)
        if user is None:
            return None
        user.role = role
        self.session.add(user)
        await self.session.flush()
        return user

    async def get_user_by_id(self, user_id: int) -> User | None:
        """Return a user by primary key.

        Args:
            user_id: User identifier.

        Returns:
            User ORM instance or `None`.
        """

        return await self.session.get(User, user_id)

    async def get_user_by_email(self, email: str) -> User | None:
        """Return a user by email.

        Args:
            email: User email address.

        Returns:
            User ORM instance or `None`.
        """

        stmt = select(User).where(User.email == email)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def mark_user_verified(self, user_id: int) -> User | None:
        """Mark a user as verified.

        Args:
            user_id: User identifier.

        Returns:
            Updated user ORM instance or `None`.
        """

        user = await self.get_user_by_id(user_id)
        if user is None:
            return None
        user.is_verified = True
        self.session.add(user)
        await self.session.flush()
        return user

    async def update_avatar_url(self, user_id: int, avatar_url: str) -> User | None:
        """Update a user's avatar URL.

        Args:
            user_id: User identifier.
            avatar_url: New avatar URL.

        Returns:
            Updated user ORM instance or `None`.
        """

        user = await self.get_user_by_id(user_id)
        if user is None:
            return None
        user.avatar_url = avatar_url
        self.session.add(user)
        await self.session.flush()
        return user
