import time
import uuid
import logging
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("middleware.request_logger")


class RequestLoggerMiddleware(BaseHTTPMiddleware):
    """
    HTTP middleware registering Correlation IDs and recording performance latency.
    """

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()

        # 1. Parse or generate Correlation ID
        correlation_id = request.headers.get("X-Correlation-ID")
        if not correlation_id:
            correlation_id = str(uuid.uuid4())

        # Store on request state scope
        request.state.correlation_id = correlation_id

        # 2. Proceed with down-stream processing
        response = await call_next(request)

        # 3. Calculate latency
        latency_ms = (time.time() - start_time) * 1000

        # 4. Log request summary
        logger.info(
            f"HTTP {request.method} {request.url.path} - "
            f"Status: {response.status_code} - Latency: {latency_ms:.2f}ms",
            extra={"correlation_id": correlation_id},
        )

        # 5. Record Prometheus HTTP Metrics
        if request.url.path != "/metrics":
            try:
                from app.utils.prometheus import (
                    HTTP_REQUEST_COUNT,
                    HTTP_REQUEST_LATENCY,
                )

                HTTP_REQUEST_COUNT.labels(
                    method=request.method,
                    endpoint=request.url.path,
                    status=response.status_code,
                ).inc()
                HTTP_REQUEST_LATENCY.labels(
                    method=request.method, endpoint=request.url.path
                ).observe(time.time() - start_time)
            except Exception as e:
                logger.error(f"Failed to record Prometheus metrics: {e}")

        # 6. Inject trace ID into response header
        response.headers["X-Correlation-ID"] = correlation_id

        return response
