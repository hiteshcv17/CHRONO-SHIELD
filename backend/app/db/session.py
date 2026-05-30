import logging
import time
import os
from typing import Any, AsyncGenerator, Optional, Union

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
import redis.asyncio as aioredis
from app.configs.settings import settings

logger = logging.getLogger("db_session")

# ==============================================================================
# Database Configuration — Dynamic selection (PostgreSQL by default / SQLite behind flag)
# ==============================================================================
USE_SQLITE_DEV = os.getenv("USE_SQLITE_DEV", "true").lower() == "true"

if settings.ENVIRONMENT == "production":
    logger.info("Connecting to production PostgreSQL database...")
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False,
        pool_pre_ping=True,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_timeout=settings.DB_POOL_TIMEOUT,
        pool_recycle=3600,
    )
elif USE_SQLITE_DEV:
    logger.info("Using local SQLite database as requested by USE_SQLITE_DEV flag...")
    SQLITE_URL = "sqlite+aiosqlite:///./chronoshield.db"
    engine = create_async_engine(
        SQLITE_URL,
        echo=False,
        connect_args={"check_same_thread": False},
    )
else:
    logger.info("Connecting to development PostgreSQL database...")
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False,
        pool_pre_ping=True,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_timeout=settings.DB_POOL_TIMEOUT,
        pool_recycle=3600,
    )

async_session_factory = async_sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
    class_=AsyncSession,
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency injection to supply async database sessions.
    """
    async with async_session_factory() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session rolled back due to error: {e}")
            raise
        finally:
            await session.close()


# ==============================================================================
# In-Memory Token Store — replaces Redis for local dev
# Stores {jti: (username, expires_at_unix)}
# ==============================================================================
class InMemoryTokenStore:
    """Thread-safe in-memory replacement for Redis refresh-token sessions."""

    def __init__(self):
        self._store: dict[str, tuple[str, float]] = {}

    async def set(self, key: str, value: str, ex: int = 0):
        expires_at = time.time() + ex if ex else float("inf")
        self._store[key] = (value, expires_at)

    async def get(self, key: str) -> Optional[str]:
        entry = self._store.get(key)
        if entry is None:
            return None
        value, expires_at = entry
        if time.time() > expires_at:
            del self._store[key]
            return None
        return value

    async def exists(self, key: str) -> int:
        return 1 if await self.get(key) is not None else 0

    async def delete(self, *keys: str) -> int:
        count = 0
        for key in keys:
            if key in self._store:
                del self._store[key]
                count += 1
        return count

    async def scan(self, cursor: int = 0, match: Optional[str] = None, count: Optional[int] = None) -> tuple[int, list[str]]:
        """Mock implementation of redis scan command for InMemoryTokenStore."""
        keys = list(self._store.keys())
        if match:
            clean_match = match.replace("*", "")
            keys = [k for k in keys if clean_match in k]
        return 0, keys

    async def ping(self) -> bool:
        return True

    async def close(self):
        pass


# Initialize Redis client in production or if a remote host/url is configured, otherwise fallback to InMemoryTokenStore
if settings.ENVIRONMENT == "production" or (settings.REDIS_HOST != "localhost"):
    logger.info(f"Connecting to Redis at {settings.REDIS_HOST}:{settings.REDIS_PORT}...")
    redis_client = aioredis.from_url(
        settings.REDIS_URL,
        decode_responses=True,
    )
else:
    logger.info("Using InMemoryTokenStore for session token cache...")
    redis_client = InMemoryTokenStore()


async def get_redis_client() -> AsyncGenerator[Union[aioredis.Redis, InMemoryTokenStore], None]:
    """
    FastAPI dependency that yields either the async Redis client or the in-memory token store.
    """
    yield redis_client
