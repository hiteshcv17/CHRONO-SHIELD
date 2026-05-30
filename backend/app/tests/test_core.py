"""
Phase 30 — Core Infrastructure Tests
Covers: app/core/metrics.py (all four functions + edge cases),
        app/core/pipeline.py (ABC contract, concrete implementations),
        app/core/registry.py (lookup, registration, error handling),
        app/core/base.py (ApiResponse, PaginatedResponse factories).
"""

import math
import pytest
import numpy as np
import asyncio
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.core import metrics as m
from app.core.pipeline import (
    ForecastingPipeline,
    ProphetPipeline,
    ArimaPipeline,
    EtsPipeline,
)
from app.core.registry import PipelineRegistry
from app.core.base import ApiResponse, PaginatedResponse, ErrorDetail


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


# ── Fixtures ─────────────────────────────────────────────────────────────────
@pytest.fixture
def simple_series():
    rng = np.random.default_rng(0)
    t = np.arange(120)
    base = 1000.0 + 0.5 * t + 200.0 * np.sin(2 * np.pi * t / 24)
    return base + rng.normal(0, 20, 120)


@pytest.fixture
def train_test(simple_series):
    return simple_series[:96], simple_series[96:]


# ==============================================================================
# ── app/core/metrics ──────────────────────────────────────────────────────────
# ==============================================================================
class TestMetrics:

    def test_mae_perfect(self):
        a = np.array([1.0, 2.0, 3.0])
        assert m.mae(a, a) == pytest.approx(0.0, abs=1e-10)

    def test_rmse_perfect(self):
        a = np.array([1.0, 2.0, 3.0])
        assert m.rmse(a, a) == pytest.approx(0.0, abs=1e-10)

    def test_mape_perfect(self):
        a = np.array([100.0, 200.0])
        assert m.mape(a, a) == pytest.approx(0.0, abs=1e-10)

    def test_r2_perfect(self):
        a = np.array([1.0, 2.0, 3.0])
        assert m.r2(a, a) == pytest.approx(1.0, abs=1e-10)

    def test_mae_known_value(self):
        a = np.array([1.0, 2.0, 3.0])
        p = np.array([2.0, 2.0, 2.0])
        assert m.mae(a, p) == pytest.approx(2.0 / 3.0, abs=1e-6)

    def test_rmse_known_value(self):
        a = np.array([0.0, 4.0])
        p = np.array([0.0, 0.0])
        assert m.rmse(a, p) == pytest.approx(math.sqrt(8.0), abs=1e-6)

    def test_mape_known_value(self):
        a = np.array([100.0, 200.0])
        p = np.array([110.0, 180.0])
        expected = (10.0 / 100.0 + 20.0 / 200.0) / 2 * 100
        assert m.mape(a, p) == pytest.approx(expected, abs=1e-4)

    def test_r2_known_bad_model(self):
        a = np.array([1.0, 2.0, 3.0, 4.0])
        p = np.full(4, 10.0)
        assert m.r2(a, p) < 0.0

    def test_rmse_ge_mae_always(self):
        rng = np.random.default_rng(1)
        a = rng.uniform(100, 500, 50)
        p = rng.uniform(100, 500, 50)
        assert m.rmse(a, p) >= m.mae(a, p)

    def test_mape_zero_actual_safe(self):
        a = np.zeros(5)
        p = np.ones(5)
        assert m.mape(a, p) == pytest.approx(0.0, abs=1e-10)

    def test_r2_flat_series(self):
        a = np.ones(10) * 42.0
        p = np.ones(10) * 42.0
        assert m.r2(a, p) == pytest.approx(1.0, abs=1e-10)

    def test_compute_all_returns_four_keys(self):
        a = np.linspace(100, 200, 20)
        p = a + 5
        result = m.compute_all(a, p)
        for key in ("mae", "rmse", "mape", "r2"):
            assert key in result, f"Missing key: {key}"

    def test_compute_all_values_finite(self):
        a = np.linspace(50, 300, 30)
        p = a * 1.05
        result = m.compute_all(a, p)
        for k, v in result.items():
            assert math.isfinite(v), f"{k}={v} is not finite"

    def test_compute_all_rounded_to_4dp(self):
        a = np.array([1.0, 3.0, 5.0])
        p = np.array([1.1, 3.0, 4.9])
        result = m.compute_all(a, p)
        for k, v in result.items():
            assert v == round(v, 4), f"{k} not rounded to 4dp"


# ==============================================================================
# ── app/core/pipeline ─────────────────────────────────────────────────────────
# ==============================================================================
class TestPipelineInterface:

    def test_arima_run_returns_dict(self, train_test):
        train, test = train_test
        pipe = ArimaPipeline()
        result = pipe.run(train, test)
        assert "model_name" in result
        assert "predicted" in result
        assert "converged" in result

    def test_arima_predicted_length(self, train_test):
        train, test = train_test
        result = ArimaPipeline().run(train, test)
        assert len(result["predicted"]) == len(test)

    def test_arima_converged(self, train_test):
        train, test = train_test
        result = ArimaPipeline().run(train, test)
        assert result["converged"] is True

    def test_arima_positive_predictions(self, train_test):
        train, test = train_test
        result = ArimaPipeline().run(train, test)
        assert np.all(result["predicted"] >= 0)

    def test_arima_has_timing(self, train_test):
        train, test = train_test
        result = ArimaPipeline().run(train, test)
        assert result["training_time_ms"] >= 0
        assert result["inference_time_ms"] >= 0

    def test_ets_run_returns_dict(self, train_test):
        train, test = train_test
        result = EtsPipeline().run(train, test)
        assert "model_name" in result

    def test_ets_predicted_length(self, train_test):
        train, test = train_test
        result = EtsPipeline().run(train, test)
        assert len(result["predicted"]) == len(test)

    def test_ets_converged(self, train_test):
        train, test = train_test
        result = EtsPipeline().run(train, test)
        assert result["converged"] is True

    def test_ets_faster_than_prophet_train(self, train_test):
        train, test = train_test
        ets_r = EtsPipeline().run(train, test)
        prophet_r = ProphetPipeline().run(train, test)
        assert ets_r["training_time_ms"] < prophet_r["training_time_ms"], (
            f"ETS ({ets_r['training_time_ms']:.0f}ms) should be faster than "
            f"Prophet ({prophet_r['training_time_ms']:.0f}ms)"
        )

    def test_pipeline_name_correct(self):
        assert ArimaPipeline.name == "ARIMA"
        assert ProphetPipeline.name == "Prophet"
        assert EtsPipeline.name == "ETS"

    def test_fit_returns_self(self, train_test):
        train, _ = train_test
        pipe = ArimaPipeline()
        returned = pipe.fit(train)
        assert returned is pipe

    def test_predict_without_fit_returns_fallback(self):
        pipe = ArimaPipeline()
        pipe._train = np.array([100.0, 200.0, 300.0])
        pipe._converged = False
        result = pipe.predict(5)
        assert len(result) == 5
        assert np.all(result >= 0)


# ==============================================================================
# ── app/core/registry ────────────────────────────────────────────────────────
# ==============================================================================
class TestRegistry:

    def test_get_prophet(self):
        p = PipelineRegistry.get("Prophet")
        assert isinstance(p, ProphetPipeline)

    def test_get_arima(self):
        p = PipelineRegistry.get("ARIMA")
        assert isinstance(p, ArimaPipeline)

    def test_get_ets(self):
        p = PipelineRegistry.get("ETS")
        assert isinstance(p, EtsPipeline)

    def test_get_unknown_raises(self):
        with pytest.raises(KeyError, match="Unknown pipeline"):
            PipelineRegistry.get("NonExistentModel")

    def test_each_call_returns_new_instance(self):
        p1 = PipelineRegistry.get("ARIMA")
        p2 = PipelineRegistry.get("ARIMA")
        assert p1 is not p2, "Registry must return fresh instances"

    def test_available_lists_all(self):
        avail = PipelineRegistry.available()
        assert "Prophet" in avail
        assert "ARIMA" in avail
        assert "ETS" in avail

    def test_custom_register(self):
        class DummyPipeline(ForecastingPipeline):
            name = "DummyTest"

            def _fit_impl(self, train):
                pass

            def _predict_impl(self, horizon):
                return np.zeros(horizon)

        PipelineRegistry.register("DummyTest", DummyPipeline)
        pipe = PipelineRegistry.get("DummyTest")
        assert isinstance(pipe, DummyPipeline)
        # Cleanup
        del PipelineRegistry._registry["DummyTest"]

    def test_ets_kwargs_forwarded(self):
        pipe = PipelineRegistry.get("ETS", seasonal_periods=12)
        assert pipe._seasonal_periods == 12


# ==============================================================================
# ── app/core/base ─────────────────────────────────────────────────────────────
# ==============================================================================
class TestBase:

    def test_api_response_ok(self):
        resp = ApiResponse.ok({"value": 42})
        assert resp.success is True
        assert resp.data == {"value": 42}
        assert resp.error is None

    def test_api_response_fail(self):
        resp = ApiResponse.fail("NOT_FOUND", "Resource not found")
        assert resp.success is False
        assert resp.data is None
        assert resp.error is not None
        assert resp.error.code == "NOT_FOUND"
        assert resp.error.message == "Resource not found"

    def test_api_response_has_timestamp(self):
        resp = ApiResponse.ok(None)
        assert resp.timestamp is not None
        assert "T" in resp.timestamp  # ISO-8601

    def test_api_response_has_request_id(self):
        resp = ApiResponse.ok(None)
        assert len(resp.request_id) == 36  # UUID v4

    def test_paginated_response_build(self):
        items = list(range(10))
        resp = PaginatedResponse.build(items=items, total=35, page=2, page_size=10)
        assert resp.total_pages == 4
        assert resp.page == 2
        assert resp.page_size == 10
        assert resp.total == 35

    def test_paginated_response_last_page(self):
        items = ["x"]
        resp = PaginatedResponse.build(items=items, total=21, page=3, page_size=10)
        assert resp.total_pages == 3

    def test_paginated_response_single_page(self):
        items = [1, 2, 3]
        resp = PaginatedResponse.build(items=items, total=3, page=1, page_size=10)
        assert resp.total_pages == 1

    def test_error_detail_fields(self):
        err = ErrorDetail(code="VALIDATION_ERROR", message="Bad input", field="score")
        assert err.field == "score"
        assert err.trace_id is None


# ==============================================================================
# ── Platform health endpoint ──────────────────────────────────────────────────
# ==============================================================================
class TestPlatformHealth:

    def test_health_endpoint_accessible(self):
        async def _a():
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.get("/api/v1/platform/health")
                assert resp.status_code == 200
                data = resp.json()
                assert "status" in data
                assert "version" in data
                assert "services" in data

        _run(_a())

    def test_health_returns_version(self):
        async def _a():
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.get("/api/v1/platform/health")
                data = resp.json()
                assert len(data["version"]) > 0

        _run(_a())

    def test_health_uptime_positive(self):
        async def _a():
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.get("/api/v1/platform/health")
                data = resp.json()
                assert data.get("uptime_seconds", -1) >= 0

        _run(_a())
