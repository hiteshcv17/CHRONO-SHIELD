import inspect
import json
import logging
from functools import wraps
from typing import Any, Callable, Optional
from pydantic import BaseModel
from fastapi.encoders import jsonable_encoder
from app.db.session import redis_client
from app.utils.prometheus import CACHE_OPERATIONS

logger = logging.getLogger("cache_utils")


def cache_response(ttl: int = 60, prefix: str = "api_cache"):
    """
    Asynchronous decorator to cache FastAPI endpoint responses using the Redis client singleton.
    Falls back to mock InMemoryTokenStore if running locally without Redis.
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Bind positional and keyword arguments to parameters
            sig = inspect.signature(func)
            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()
            
            # Construct a deterministic cache key based on non-injected query/path params
            key_parts = []
            for k, v in sorted(bound_args.arguments.items()):
                # Exclude dependencies from the cache key serialization
                if k in ("db", "current_user", "redis", "background_tasks"):
                    continue
                if isinstance(v, BaseModel):
                    v = json.dumps(v.model_dump(), sort_keys=True)
                key_parts.append(f"{k}={v}")
            
            # Form cache key
            serialized_args = ":".join(key_parts)
            cache_key = f"{prefix}:{func.__name__}:{serialized_args}"
            
            # Check cache
            try:
                cached_val = await redis_client.get(cache_key)
                if cached_val is not None:
                    logger.debug(f"Cache HIT for key: {cache_key}")
                    CACHE_OPERATIONS.labels(prefix=prefix, operation="read", status="hit").inc()
                    # Return the raw deserialized JSON
                    return json.loads(cached_val)
                else:
                    CACHE_OPERATIONS.labels(prefix=prefix, operation="read", status="miss").inc()
            except Exception as e:
                CACHE_OPERATIONS.labels(prefix=prefix, operation="read", status="failure").inc()
                logger.error(f"Cache read failed for key {cache_key}: {e}")
            
            # Call route function
            result = await func(*args, **kwargs)
            
            # Store in cache
            try:
                serialized_result = jsonable_encoder(result)
                await redis_client.set(cache_key, json.dumps(serialized_result), ex=ttl)
                CACHE_OPERATIONS.labels(prefix=prefix, operation="write", status="success").inc()
                logger.debug(f"Cache MISS. Saved data to key: {cache_key} with TTL={ttl}s")
            except Exception as e:
                CACHE_OPERATIONS.labels(prefix=prefix, operation="write", status="failure").inc()
                logger.error(f"Cache write failed for key {cache_key}: {e}")
                
            return result
        return wrapper
    return decorator


async def invalidate_cache_by_pattern(pattern: str) -> None:
    """
    Invalidates all keys matching a specific pattern.
    Supports both real async redis client and InMemoryTokenStore fallback.
    """
    prefix = pattern.split(":")[0] if ":" in pattern else pattern
    try:
        if hasattr(redis_client, "_store"):  # InMemoryTokenStore
            # Normalize pattern to remove wildcards for in-memory matching
            clean_pattern = pattern.replace("*", "")
            keys_to_del = [k for k in redis_client._store.keys() if clean_pattern in k]
            for k in keys_to_del:
                await redis_client.delete(k)
            logger.info(f"Invalidated {len(keys_to_del)} local in-memory cache keys using pattern '{pattern}'")
        else:  # Real Redis asyncio client
            cursor = 0
            keys_deleted = 0
            while True:
                cursor, keys = await redis_client.scan(cursor, match=pattern)
                if keys:
                    await redis_client.delete(*keys)
                    keys_deleted += len(keys)
                if cursor == 0:
                    break
            logger.info(f"Invalidated {keys_deleted} Redis cache keys using pattern '{pattern}'")
        CACHE_OPERATIONS.labels(prefix=prefix, operation="invalidate", status="success").inc()
    except Exception as e:
        CACHE_OPERATIONS.labels(prefix=prefix, operation="invalidate", status="failure").inc()
        logger.error(f"Failed to invalidate cache with pattern '{pattern}': {e}")
