import time
import logging
from typing import Dict, Tuple
from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.db.session import redis_client, async_session_factory
from app.models.system_setting import SystemSetting
from app.core.base import ApiResponse
from sqlalchemy import select

logger = logging.getLogger("middleware.rate_limiter")

# Local cache for settings to prevent DB flooding if Redis is unavailable
_SETTINGS_CACHE: Dict[str, Tuple[bool, float]] = {}  # key -> (value, expiry_timestamp)

# In-memory rate limiting store fallback if Redis is offline
_IN_MEMORY_LIMITS: Dict[str, list] = {}  # client_ip -> list of timestamps


async def is_rate_limiting_enabled() -> bool:
    """
    Checks if rate limiting is enabled.
    Checks Redis first. Falls back to SQLite database with a 5s local cache TTL if Redis is offline.
    """
    # 1. Check Redis Cache
    try:
        val = await redis_client.get("settings:rate_limiting_enabled")
        if val is not None:
            return val.decode("utf-8").lower() == "true" if isinstance(val, bytes) else str(val).lower() == "true"
    except Exception as re:
        logger.warning(f"Failed to query Redis settings cache: {re}")

    # 2. Check local 5s memory cache
    now = time.time()
    cache_key = "rate_limiting_enabled"
    if cache_key in _SETTINGS_CACHE:
        val, expiry = _SETTINGS_CACHE[cache_key]
        if now < expiry:
            return val

    # 3. Fallback to SQL Database
    try:
        async with async_session_factory() as session:
            stmt = select(SystemSetting).where(SystemSetting.key == "rate_limiting_enabled")
            res = await session.execute(stmt)
            setting = res.scalar_one_or_none()
            enabled = True  # default
            if setting:
                enabled = setting.value.lower() == "true"
            # Cache locally for 5s
            _SETTINGS_CACHE[cache_key] = (enabled, now + 5.0)
            return enabled
    except Exception as de:
        logger.error(f"Failed to query database for settings: {de}")
        # Default to True for maximum security on query failures
        return True


class RateLimitingMiddleware(BaseHTTPMiddleware):
    """
    FastAPI HTTP rate limiter middleware enforcing a threshold of 100 requests
    per minute per client IP. Powered by Redis with high-performance memory fallbacks.
    """
    async def dispatch(self, request: Request, call_next):
        # Only rate limit endpoints under the API prefix /api/
        if not request.url.path.startswith("/api/"):
            return await call_next(request)

        # Check if rate limiting toggle is active
        enabled = await is_rate_limiting_enabled()
        if not enabled:
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        current_minute = int(time.time() // 60)
        limit = 100  # max requests per minute

        # 1. Enforce using Redis (Primary production mechanism)
        try:
            redis_key = f"rate_limit:{client_ip}:{current_minute}"
            # Increment request counter
            req_count = await redis_client.incr(redis_key)
            if req_count == 1:
                # Set TTL for 60 seconds on the first request of this minute
                await redis_client.expire(redis_key, 60)
                
            if req_count > limit:
                logger.warning(f"Rate limit breached for IP {client_ip} on Redis (requests: {req_count}/{limit})")
                err_envelope = ApiResponse.fail(
                    code="TOO_MANY_REQUESTS",
                    message="API rate limit exceeded (100 req/min). Please try again later."
                )
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content=err_envelope.model_dump(),
                    headers={"Retry-After": "60"}
                )
        # 2. Enforce using In-Memory Fallback (Local resilient fallback)
        except Exception as e:
            logger.debug(f"Redis rate limiting offline, falling back to local memory: {e}")
            now = time.time()
            # Clean old timestamps older than 60 seconds
            if client_ip not in _IN_MEMORY_LIMITS:
                _IN_MEMORY_LIMITS[client_ip] = []
            _IN_MEMORY_LIMITS[client_ip] = [t for t in _IN_MEMORY_LIMITS[client_ip] if now - t < 60]
            
            req_count = len(_IN_MEMORY_LIMITS[client_ip])
            if req_count >= limit:
                logger.warning(f"Rate limit breached for IP {client_ip} in-memory (requests: {req_count + 1}/{limit})")
                err_envelope = ApiResponse.fail(
                    code="TOO_MANY_REQUESTS",
                    message="API rate limit exceeded (100 req/min). Please try again later."
                )
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content=err_envelope.model_dump(),
                    headers={"Retry-After": "60"}
                )
            
            _IN_MEMORY_LIMITS[client_ip].append(now)

        return await call_next(request)
