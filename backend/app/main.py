import logging
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.configs.settings import settings
from app.utils.logging import setup_logging
from app.middleware.request_logger import RequestLoggerMiddleware
from app.middleware.error_handler import GlobalErrorHandlerMiddleware, register_exception_handlers
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.middleware.validation import PayloadValidationMiddleware
from app.middleware.rate_limiter import RateLimitingMiddleware
from app.routes import diagnostics
from app.routes.v1 import (
    anomaly, weather, traffic, correlation,
    forecasting, health, social, alert, geo,
    replay, explain, benchmark, auth, notification, report, asset,
    system_settings,
)
from app.db.session import engine, redis_client, async_session_factory
from app.core.auth import get_current_user

# ---------------------------------------------------------------------------
# Logging bootstrap (must happen before any other import that logs)
# ---------------------------------------------------------------------------
setup_logging(log_level=settings.BACKEND_LOG_LEVEL, logs_dir=settings.LOGS_DIR)
logger = logging.getLogger("main")

# Track startup time for uptime reporting
_START_TIME = time.monotonic()


# ==============================================================================
# Application lifespan
# ==============================================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manages startup connections and graceful shutdown."""
    logger.info("ChronoShield AI — starting up...")

    # Database table synchronization
    try:
        # Assert database schema is managed via Alembic in production
        if settings.ENVIRONMENT == "production":
            logger.info("Asserting database schema is managed and migrated by Alembic...")
            from sqlalchemy import text
            async with async_session_factory() as session:
                try:
                    res = await session.execute(text("SELECT version_num FROM alembic_version"))
                    version = res.scalar()
                    logger.info(f"Database migrated via Alembic. Current Revision: {version}")
                except Exception as e:
                    logger.error("CRITICAL: Alembic schema version check failed! Ensure 'alembic upgrade head' was run.")
                    raise RuntimeError("Database schema is not migrated or managed by Alembic!") from e
        else:
            # Dev auto-sync fallback for local convenience and pytest suites
            async with engine.begin() as conn:
                from app.models.base import Base
                from app.models.anomaly import AnomalyRecord        # noqa: F401
                from app.models.weather import WeatherRecordModel   # noqa: F401
                from app.models.traffic import TrafficRecordModel   # noqa: F401
                from app.models.energy import EnergyRecordModel     # noqa: F401
                from app.models.social import SocialComplaintRecord # noqa: F401
                from app.models.alert import PrioritizedAlertRecord # noqa: F401
                from app.models.user import User                    # noqa: F401
                from app.models.notification import (               # noqa: F401
                    NotificationChannelConfig,
                    NotificationDeliveryLog
                )
                from app.models.report import Report                # noqa: F401
                from app.models.asset import Asset                  # noqa: F401
                from app.models.system_setting import SystemSetting # noqa: F401
                await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables synchronized via dev auto-sync.")

        # Seed default admin user if none exists
        from sqlalchemy import select
        from app.models.user import User
        from app.core.security import get_password_hash
        async with async_session_factory() as session:
            stmt = select(User).where(User.username == "admin")
            res = await session.execute(stmt)
            if not res.scalar_one_or_none():
                admin_user = User(
                    username="admin",
                    email="admin@chronoshield.ai",
                    hashed_password=get_password_hash("chronoshield"),
                    role="ADMIN",
                    is_active=True
                )
                session.add(admin_user)
                await session.commit()
                logger.info("Default administrator seeded (admin / chronoshield).")

            # Seed default notification configurations
            from app.models.notification import NotificationChannelConfig
            import json
            for c_type, cfg_data in [
                ("EMAIL", {"recipient_email": "operator@chronoshield.ai", "smtp_host": "localhost", "smtp_port": 1025, "allowed_severities": ["LOW", "MEDIUM", "HIGH", "CRITICAL"]}),
                ("TELEGRAM", {"bot_token": "MOCK_TELEGRAM_TOKEN", "chat_id": "MOCK_CHAT_ID", "allowed_severities": ["HIGH", "CRITICAL"]}),
                ("WEBHOOK", {"webhook_url": "http://localhost:8000/api/v1/notifications/webhook-test", "allowed_severities": ["MEDIUM", "HIGH", "CRITICAL"]})
            ]:
                stmt_c = select(NotificationChannelConfig).where(NotificationChannelConfig.channel_type == c_type)
                res_c = await session.execute(stmt_c)
                if not res_c.scalar_one_or_none():
                    new_cfg = NotificationChannelConfig(
                        channel_type=c_type,
                        config=json.dumps(cfg_data),
                        enabled=False
                    )
                    session.add(new_cfg)
            await session.commit()
            logger.info("Default notification channel configurations seeded.")

            # Seed default system settings
            from app.models.system_setting import SystemSetting
            stmt_s = select(SystemSetting).where(SystemSetting.key == "rate_limiting_enabled")
            res_s = await session.execute(stmt_s)
            if not res_s.scalar_one_or_none():
                new_setting = SystemSetting(key="rate_limiting_enabled", value="true")
                session.add(new_setting)
                await session.commit()
                try:
                    await redis_client.set("settings:rate_limiting_enabled", "true")
                except Exception as re:
                    logger.warning(f"Could not seed Redis settings cache: {re}")
                logger.info("Default system setting 'rate_limiting_enabled' seeded to true.")

            # Seed default reports if none exist
            from app.models.report import Report
            from app.services.report_service import ReportService
            from datetime import datetime, timedelta
            stmt_r = select(Report)
            res_r = await session.execute(stmt_r)
            if not res_r.scalars().first():
                now = datetime.utcnow()
                await ReportService.generate_executive_report(session, "DAILY", now - timedelta(days=1), now)
                await ReportService.generate_executive_report(session, "WEEKLY", now - timedelta(days=7), now)
                logger.info("Default daily and weekly executive reports generated and seeded.")

            # Seed default assets if none exist
            from app.models.asset import Asset
            stmt_a = select(Asset)
            res_a = await session.execute(stmt_a)
            if not res_a.scalars().first():
                from app.schemas.asset import AssetCreate
                from app.services.asset_service import AssetService
                for name, atype, status, region, metadata in [
                    ("North Grid Substation Transformer T-01", "TRANSFORMER", "NOMINAL", "North Sector", {"capacity_kva": 2500, "voltage_kv": 13.8}),
                    ("Main St Intersection Camera & Controller", "TRAFFIC_ZONE", "WARNING", "Downtown Grid", {"avg_daily_flow": 18200, "camera_status": "ONLINE"}),
                    ("Central Trunk Aqueduct Conduit B", "WATER_PIPELINE", "CRITICAL", "Central Hub", {"pipe_diameter_in": 36, "flow_rate_lps": 480.5}),
                    ("District 7 Warning Siren Tower", "PUBLIC_SYSTEM", "NOMINAL", "South Sector", {"decibel_output": 120, "coverage_radius_m": 800})
                ]:
                    await AssetService.create_asset(
                        session,
                        AssetCreate(
                            name=name,
                            asset_type=atype,
                            status=status,
                            region=region,
                            dynamic_metadata=metadata
                        )
                    )
                logger.info("Default infrastructure assets seeded.")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")

    # Redis connectivity check
    try:
        await redis_client.ping()
        logger.info("Redis cache linked.")
    except Exception as e:
        logger.error(f"Redis initialization failed: {e}")

    logger.info("ChronoShield AI — ready.")
    yield

    logger.info("ChronoShield AI — shutting down...")
    await engine.dispose()
    await redis_client.close()
    logger.info("ChronoShield AI — shutdown complete.")


# ==============================================================================
# FastAPI application
# ==============================================================================
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=(
        "Enterprise Temporal Anomaly Detection & Predictive Infrastructure Analytics.\n\n"
        "Multi-source correlation engine • Explainable AI • Model benchmarking • "
        "Geospatial monitoring • Historical incident replay."
    ),
    contact={
        "name": "ChronoShield AI Engineering",
        "url": "https://chronoshield.ai",
    },
    license_info={
        "name": "Proprietary",
        "url": "https://chronoshield.ai/license",
    },
    lifespan=lifespan,
)

# Mount static files directory for reports downloads
from fastapi.staticfiles import StaticFiles
import os
os.makedirs("static/reports", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# ==============================================================================
# Middleware (order matters — outer middleware executes first on request,
# last on response)
# ==============================================================================

# GZip compression for responses > 1 KB
app.add_middleware(GZipMiddleware, minimum_size=1024)

# Request/response logging with correlation IDs
app.add_middleware(RequestLoggerMiddleware)

# Security Hardening Middlewares
# Enforce dynamic API rate limiting per IP
app.add_middleware(RateLimitingMiddleware)

# Enforce mutative request size checks (DoS mitigation)
app.add_middleware(PayloadValidationMiddleware)

# Enforce secure HTTP headers (OWASP standards)
app.add_middleware(SecurityHeadersMiddleware)

# Global structured error handler
app.add_middleware(GlobalErrorHandlerMiddleware)
register_exception_handlers(app)

# CORS — allow configured origins
cors_origins = settings.BACKEND_CORS_ORIGINS
if isinstance(cors_origins, str):
    cors_origins = [cors_origins]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==============================================================================
# Platform health endpoint (liveness probe)
# ==============================================================================
@app.get(
    f"{settings.API_V1_STR}/platform/health",
    tags=["Platform"],
    summary="Liveness / readiness probe",
)
async def platform_health():
    """
    Returns the platform health status including uptime and service connectivity.
    Used by load balancers and orchestrators for liveness/readiness checks.
    """
    from app.core.base import PlatformHealthResponse, ServiceHealth

    services = []

    # Database probe
    try:
        async with engine.connect() as conn:
            await conn.execute(__import__("sqlalchemy", fromlist=["text"]).text("SELECT 1"))
        services.append(ServiceHealth(name="postgresql", status="healthy"))
    except Exception as e:
        services.append(ServiceHealth(name="postgresql", status="unavailable", detail=str(e)[:100]))

    # Redis probe
    try:
        await redis_client.ping()
        services.append(ServiceHealth(name="redis", status="healthy"))
    except Exception as e:
        services.append(ServiceHealth(name="redis", status="unavailable", detail=str(e)[:100]))

    overall = "healthy" if all(s.status == "healthy" for s in services) else "degraded"

    return PlatformHealthResponse(
        status=overall,
        version=settings.VERSION,
        uptime_seconds=round(time.monotonic() - _START_TIME, 1),
        services=services,
    )


@app.get(
    "/metrics",
    tags=["Platform"],
    summary="Prometheus metrics",
)
async def metrics():
    """
    Prometheus metrics scrape endpoint.
    Retrieves active database alert counts dynamically to update gauge.
    """
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
    from fastapi import Response
    try:
        from app.utils.prometheus import ACTIVE_ALERTS
        from app.models.alert import PrioritizedAlertRecord
        from sqlalchemy import select, func
        
        ACTIVE_ALERTS.clear()
        
        async with async_session_factory() as session:
            stmt = select(
                PrioritizedAlertRecord.current_severity,
                PrioritizedAlertRecord.status,
                func.count(PrioritizedAlertRecord.id)
            ).group_by(
                PrioritizedAlertRecord.current_severity,
                PrioritizedAlertRecord.status
            )
            res = await session.execute(stmt)
            for severity, status, count in res.all():
                ACTIVE_ALERTS.labels(severity=severity, status=status).set(count)
    except Exception as e:
        logger.error(f"Failed to update active alerts gauge: {e}")
        
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


# ==============================================================================
# API Router registration
# ==============================================================================
app.include_router(diagnostics.router, tags=["Diagnostics"])

_V1 = settings.API_V1_STR

app.include_router(auth.router,         prefix=f"{_V1}/auth",        tags=["Authentication"])
app.include_router(anomaly.router,      prefix=f"{_V1}/anomaly",     tags=["Temporal Anomalies"])
app.include_router(alert.router,        prefix=f"{_V1}/alerts",      tags=["Intelligent Alerts"])
app.include_router(weather.router,      prefix=f"{_V1}/weather",     tags=["Weather Telemetry"])
app.include_router(traffic.router,      prefix=f"{_V1}/traffic",     tags=["Traffic Telemetry"])
app.include_router(correlation.router,  prefix=f"{_V1}/correlation", tags=["Correlation Analytics"])
app.include_router(forecasting.router,  prefix=f"{_V1}/forecasting", tags=["Predictive Forecasting"])
app.include_router(health.router,       prefix=f"{_V1}/health",      tags=["Infrastructure Health"])
app.include_router(social.router,       prefix=f"{_V1}/social",      tags=["Social Media Signals"])
app.include_router(geo.router,          prefix=f"{_V1}/geo",         tags=["Geospatial Infrastructure"])
app.include_router(replay.router,       prefix=f"{_V1}/replay",      tags=["Historical Replay"])
app.include_router(explain.router,      prefix=f"{_V1}/explain",     tags=["Explainable AI"])
app.include_router(benchmark.router,    prefix=f"{_V1}/benchmark",   tags=["Model Benchmarking"])
app.include_router(notification.router, prefix=f"{_V1}/notifications", tags=["Notification Delivery"])
app.include_router(report.router,       prefix=f"{_V1}/reports",       tags=["Infrastructure Reports"])
app.include_router(asset.router,        prefix=f"{_V1}/assets",        tags=["Infrastructure Assets"])
app.include_router(system_settings.router, prefix=f"{_V1}/settings",      tags=["System Settings"])
