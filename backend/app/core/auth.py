from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.configs.settings import settings
from app.db.session import get_db_session
from app.core.security import decode_token
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login", auto_error=False
)


async def get_current_user(
    db: AsyncSession = Depends(get_db_session),
    token: Optional[str] = Depends(oauth2_scheme),
) -> User:
    """
    Dependency injection to fetch the authenticated User from the database.
    Verifies JWT token integrity, expiration, and ensures user account is active.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not token:
        raise credentials_exception

    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        raise credentials_exception

    username: str = payload.get("sub")
    if username is None:
        raise credentials_exception

    stmt = select(User).where(User.username == username)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User account is deactivated",
        )

    return user


class RoleChecker:
    """
    FastAPI dependency that enforces user roles.
    Allows access if the user's role is in the allowed list, otherwise raises 403.
    """

    def __init__(self, allowed_roles: list[str]):
        self.allowed_roles = allowed_roles

    def __call__(self, current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: role '{current_user.role}' lacks required permission.",
            )
        return current_user


# Pre-defined dependency instances
require_admin = RoleChecker(["ADMIN"])
require_analyst = RoleChecker(["ADMIN", "ANALYST"])
require_viewer = RoleChecker(["ADMIN", "ANALYST", "VIEWER"])
