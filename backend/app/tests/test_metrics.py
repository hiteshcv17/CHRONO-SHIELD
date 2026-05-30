"""
tests/test_metrics.py

Unit tests for Prometheus metrics and /metrics endpoint.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock


# ==============================================================================
# Prometheus utility tests
# ==============================================================================


class TestPrometheusUtilities:
    """Test Prometheus metric declarations."""

    def test_http_request_count_counter(self):
        from app.utils.prometheus import HTTP_REQUEST_COUNT
        from prometheus_client import Counter

        assert isinstance(HTTP_REQUEST_COUNT, Counter)

    def test_http_request_latency_histogram(self):
        from app.utils.prometheus import HTTP_REQUEST_LATENCY
        from prometheus_client import Histogram

        assert isinstance(HTTP_REQUEST_LATENCY, Histogram)

    def test_active_alerts_gauge(self):
        from app.utils.prometheus import ACTIVE_ALERTS
        from prometheus_client import Gauge

        assert isinstance(ACTIVE_ALERTS, Gauge)

    def test_cache_operations_counter(self):
        from app.utils.prometheus import CACHE_OPERATIONS
        from prometheus_client import Counter

        assert isinstance(CACHE_OPERATIONS, Counter)

    def test_http_request_count_can_increment(self):
        from app.utils.prometheus import HTTP_REQUEST_COUNT

        HTTP_REQUEST_COUNT.labels(method="GET", endpoint="/test", status=200).inc()
        # No assertion beyond no exception raised

    def test_http_request_latency_can_observe(self):
        from app.utils.prometheus import HTTP_REQUEST_LATENCY

        HTTP_REQUEST_LATENCY.labels(method="GET", endpoint="/test").observe(0.05)

    def test_active_alerts_gauge_can_be_set(self):
        from app.utils.prometheus import ACTIVE_ALERTS

        ACTIVE_ALERTS.labels(severity="HIGH", status="ACTIVE").set(5)

    def test_cache_operations_hit_increment(self):
        from app.utils.prometheus import CACHE_OPERATIONS

        CACHE_OPERATIONS.labels(
            prefix="api_cache", operation="read", status="hit"
        ).inc()

    def test_cache_operations_miss_increment(self):
        from app.utils.prometheus import CACHE_OPERATIONS

        CACHE_OPERATIONS.labels(
            prefix="api_cache", operation="read", status="miss"
        ).inc()

    def test_cache_operations_write_increment(self):
        from app.utils.prometheus import CACHE_OPERATIONS

        CACHE_OPERATIONS.labels(
            prefix="api_cache", operation="write", status="success"
        ).inc()


# ==============================================================================
# /metrics endpoint tests
# ==============================================================================


@pytest.fixture
def mock_app_client():
    """Create test client with mocked DB and Redis dependencies."""
    import asyncio
    from unittest.mock import AsyncMock, patch
    from app.main import app

    # Mock the async_session_factory so /metrics can run without real DB
    mock_result = MagicMock()
    mock_result.all.return_value = [
        ("HIGH", "ACTIVE", 5),
        ("MEDIUM", "ACKNOWLEDGED", 2),
        ("CRITICAL", "ESCALATED", 1),
    ]

    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)
    mock_session.execute = AsyncMock(return_value=mock_result)

    mock_factory = MagicMock(return_value=mock_session)

    with patch("app.main.async_session_factory", mock_factory):
        with TestClient(app, raise_server_exceptions=False) as client:
            yield client


class TestMetricsEndpoint:
    """Test /metrics endpoint returns valid Prometheus text output."""

    def test_metrics_endpoint_returns_200(self, mock_app_client):
        response = mock_app_client.get("/metrics")
        assert response.status_code == 200

    def test_metrics_endpoint_returns_text_content_type(self, mock_app_client):
        response = mock_app_client.get("/metrics")
        assert "text/plain" in response.headers["content-type"]

    def test_metrics_endpoint_body_is_non_empty(self, mock_app_client):
        response = mock_app_client.get("/metrics")
        assert len(response.content) > 0

    def test_metrics_contains_http_requests_total(self, mock_app_client):
        response = mock_app_client.get("/metrics")
        assert b"http_requests_total" in response.content

    def test_metrics_contains_cache_operations_total(self, mock_app_client):
        response = mock_app_client.get("/metrics")
        assert b"cache_operations_total" in response.content

    def test_metrics_contains_active_alerts_count(self, mock_app_client):
        response = mock_app_client.get("/metrics")
        assert b"active_alerts_count" in response.content

    def test_metrics_contains_http_request_duration(self, mock_app_client):
        response = mock_app_client.get("/metrics")
        assert b"http_request_duration_seconds" in response.content
