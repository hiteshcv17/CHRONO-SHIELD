import os
import time
import logging
from datetime import datetime
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from fastapi.responses import PlainTextResponse
from src.config import ai_settings
from src.ml.registry import ModelRegistryManager
from src.api.v1.endpoints import predict, registry
from src.ingestion.orchestrator import IngestionOrchestrator
from src.utils.logging import setup_logging

# ---------------------------------------------------------------------------
# Logging bootstrap — dual-stream (JSON stdout + file logs at /app/logs/ai-engine.log)
# ---------------------------------------------------------------------------
_LOGS_DIR = os.environ.get("AI_LOGS_DIR", "./logs")
setup_logging(log_level=ai_settings.AI_LOG_LEVEL.upper(), logs_dir=_LOGS_DIR)
logger = logging.getLogger("ai_service")

# Track startup time for uptime reporting
_START_TIME = time.monotonic()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ASGI Startup tasks
    logger.info("Initializing modular AI Engine microservice service layer...")
    app.state.registry = ModelRegistryManager()
    
    # Pre-verify active PRODUCTION model
    prod_path = app.state.registry.get_tier_checkpoint("PRODUCTION")
    if prod_path:
        logger.info(f"Active PRODUCTION model checkpoint detected: {prod_path}")
    else:
        logger.warning("No active checkpoint promoted to PRODUCTION tier yet.")
        
    # Initialize and start background data ingestion orchestrator
    logger.info("Starting background ingestion orchestrator...")
    orchestrator = IngestionOrchestrator()
    app.state.orchestrator = orchestrator
    await orchestrator.start()
    
    yield
    # ASGI Shutdown tasks
    logger.info("Shutting down background ingestion orchestrator...")
    orchestrator = getattr(app.state, "orchestrator", None)
    if orchestrator:
        await orchestrator.stop()
    logger.info("Shutting down AI Engine microservice ASGI channels...")


app = FastAPI(
    title="ChronoShield AI Engine API",
    description="Production-grade REST microservice interface for automated time-series anomaly detection & model registry.",
    version="1.0.0",
    lifespan=lifespan
)


# ==============================================================================
# HTTP Middleware — Prometheus metrics recording
# ==============================================================================

@app.middleware("http")
async def prometheus_middleware(request: Request, call_next):
    """
    Records HTTP request counts and latencies per endpoint for Prometheus scraping.
    Skips instrumentation for the /metrics scrape endpoint itself.
    """
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time

    if request.url.path != "/metrics":
        try:
            from src.utils.prometheus import HTTP_REQUEST_COUNT, HTTP_REQUEST_LATENCY
            HTTP_REQUEST_COUNT.labels(
                method=request.method,
                endpoint=request.url.path,
                status=response.status_code
            ).inc()
            HTTP_REQUEST_LATENCY.labels(
                method=request.method,
                endpoint=request.url.path
            ).observe(duration)
        except Exception as e:
            logger.error(f"Failed to record Prometheus HTTP metrics: {e}")

    return response


# Register router endpoints
app.include_router(predict.router, prefix="/api/v1")
app.include_router(registry.router, prefix="/api/v1")


# ==============================================================================
# Platform health & metrics endpoints
# ==============================================================================

@app.get("/health", tags=["System Health"])
def health_check():
    """
    Diagnostic service check returning active system health indicators and active models.
    """
    reg = getattr(app.state, "registry", None)
    prod_model = None
    if reg:
        try:
            prod_model = reg._load_metadata()["tiers"].get("PRODUCTION")
        except Exception:
            pass

    return {
        "status": "healthy",
        "environment": ai_settings.ENVIRONMENT,
        "active_production_model": prod_model,
        "uptime_seconds": round(time.monotonic() - _START_TIME, 1),
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/metrics", tags=["System Health"], response_class=PlainTextResponse)
def metrics_endpoint():
    """
    Prometheus metrics scrape endpoint.
    Exposes HTTP request rates, anomaly detection counts, inference latencies,
    model training durations, and ingestion pipeline throughput.
    """
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
