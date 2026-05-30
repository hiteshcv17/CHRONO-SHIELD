import time
import os
import logging
try:
    import psutil
except ImportError:
    psutil = None
import threading
from fastapi import APIRouter, status
from app.configs.settings import settings
from app.schemas.diagnostics import HealthResponse, StatusResponse, VersionResponse, DependencyStatus
from app.db.session import engine, redis_client

router = APIRouter()
logger = logging.getLogger("routes.diagnostics")


@router.get("/health", response_model=HealthResponse, status_code=status.HTTP_200_OK)
async def get_health() -> HealthResponse:
    """
    Simple container status check for routing gateway metrics.
    """
    return HealthResponse(
        status="healthy",
        service=settings.PROJECT_NAME,
        environment=settings.ENVIRONMENT
    )


@router.get("/status", response_model=StatusResponse, status_code=status.HTTP_200_OK)
async def get_status() -> StatusResponse:
    """
    Comprehensive diagnostics reporting pings across storage and cache engines.
    """
    dependencies = []
    aggregated_status = "operational"

    # 1. Database Health Check
    from sqlalchemy import text
    pg_start = time.time()
    pg_connected = False
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
            pg_connected = True
    except Exception as e:
        logger.error(f"Database connection ping failed: {e}")
        aggregated_status = "degraded"
    
    pg_latency = (time.time() - pg_start) * 1000
    dependencies.append(
        DependencyStatus(name="Database Connection", connected=pg_connected, latency_ms=round(pg_latency, 2))
    )

    # 2. Redis Stream Check
    redis_start = time.time()
    redis_connected = False
    try:
        await redis_client.ping()
        redis_connected = True
    except Exception as e:
        logger.error(f"Redis connection ping failed: {e}")
        aggregated_status = "degraded"

    redis_latency = (time.time() - redis_start) * 1000
    dependencies.append(
        DependencyStatus(name="Redis Cache Stream", connected=redis_connected, latency_ms=round(redis_latency, 2))
    )

    # Compile system metrics dynamically using psutil
    try:
        # os.getloadavg() returns 1, 5, 15 minutes load averages
        load_1m = os.getloadavg()[0]
    except (AttributeError, OSError):
        if psutil:
            load_1m = psutil.cpu_percent(interval=None) / 100.0
        else:
            load_1m = 0.28  # mock fallback

    try:
        if psutil:
            mem_pct = psutil.virtual_memory().percent
        else:
            mem_pct = 42.5  # mock fallback
    except Exception:
        mem_pct = 50.0

    try:
        if psutil:
            threads = psutil.Process().num_threads()
        else:
            threads = threading.active_count()
    except Exception:
        threads = threading.active_count()

    system_metrics = {
        "load_average_1m": round(load_1m, 2),
        "memory_allocated_pct": round(mem_pct, 1),
        "active_threads_count": threads
    }

    return StatusResponse(
        status=aggregated_status,
        dependencies=dependencies,
        system_metrics=system_metrics
    )


@router.get("/version", response_model=VersionResponse, status_code=status.HTTP_200_OK)
async def get_version() -> VersionResponse:
    """
    Exposes application core version coordinates.
    """
    return VersionResponse(
        service=settings.PROJECT_NAME,
        version=settings.VERSION,
        api_v1_prefix=settings.API_V1_STR
    )
