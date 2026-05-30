import logging
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import status

from app.models.user import User
from app.schemas.user import UserRegister
from app.core.security import get_password_hash
from app.core.exceptions import AppHTTPException, ErrorCode

logger = logging.getLogger("user_service")


class UserService:
    """Service class managing user accounts, registration, and credential hashing."""

    @staticmethod
    async def get_user_by_username(db: AsyncSession, username: str) -> Optional[User]:
        """Fetch user by unique username.

        Args:
            db: Active database session.
            username: The unique username to find.

        Returns:
            The User instance if found, otherwise None.
        """
        stmt = select(User).where(User.username == username)
        res = await db.execute(stmt)
        return res.scalar_one_or_none()

    @staticmethod
    async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
        """Fetch user by unique email.

        Args:
            db: Active database session.
            email: The unique email to find.

        Returns:
            The User instance if found, otherwise None.
        """
        stmt = select(User).where(User.email == email)
        res = await db.execute(stmt)
        return res.scalar_one_or_none()

    @staticmethod
    async def create_user(db: AsyncSession, user_in: UserRegister) -> User:
        """Register a new user account with hashed password credentials.

        Performs duplicate checks on username and email before persisting.

        Args:
            db: Active database session.
            user_in: The user registration Pydantic schema.

        Returns:
            The newly created and persisted User instance.

        Raises:
            AppHTTPException: If username or email is already taken.
        """
        # Duplicate Username Check
        existing_username = await UserService.get_user_by_username(db, user_in.username)
        if existing_username:
            raise AppHTTPException(
                error_code=ErrorCode.ALREADY_EXISTS,
                message="Username is already taken",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # Duplicate Email Check
        if user_in.email:
            existing_email = await UserService.get_user_by_email(db, user_in.email)
            if existing_email:
                raise AppHTTPException(
                    error_code=ErrorCode.ALREADY_EXISTS,
                    message="Email is already registered",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

        new_user = User(
            username=user_in.username,
            email=user_in.email,
            hashed_password=get_password_hash(user_in.password),
            role=user_in.role or "VIEWER",
            is_active=True,
        )
        try:
            db.add(new_user)
            await db.commit()
            await db.refresh(new_user)
            logger.info(f"Successfully registered new user: {new_user.username}")
            return new_user
        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to persist new user {user_in.username}: {e}")
            raise AppHTTPException(
                error_code=ErrorCode.SERVICE_UNAVAILABLE,
                message="Failed to persist user due to database error.",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            ) from e
