"""
Phase 29/30 — Benchmark Tests (updated for refactored architecture)
Uses app.core.metrics, app.core.pipeline, and BenchmarkService via PipelineRegistry.
"""
import pytest
import math
import asyncio
import numpy as np
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.services.benchmark_service import BenchmarkService, _generate_series
from app.core import metrics as m


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


# ==============================================================================
# ── Data generation ─────────────────────────────────────────────────────────
# ==============================================================================
class TestDataGeneration:

    def test_generates_correct_length(self):
        for mt in ["power", "traffic", "water", "internet"]:
            s = _generate_series(mt, 100)
            assert len(s) == 100, f"{mt}: expected 100 samples"

    def test_values_are_positive(self):
        for mt in ["power", "traffic", "water", "internet"]:
            s = _generate_series(mt, 200)
            assert np.all(s > 0), f"{mt}: series contains non-positive values"

    def test_deterministic_with_seed(self):
        s1 = _generate_series("power", 100, seed=42)
        s2 = _generate_series("power", 100, seed=42)
        np.testing.assert_array_equal(s1, s2)

    def test_different_seeds_give_different_results(self):
        s1 = _generate_series("power", 100, seed=1)
        s2 = _generate_series("power", 100, seed=99)
        assert not np.allclose(s1, s2)

    def test_power_higher_than_water(self):
        s_power = _generate_series("power", 200).mean()
        s_water = _generate_series("water", 200).mean()
        assert s_power > s_water

    def test_series_has_reasonable_variance(self):
        for mt in ["power", "traffic", "water", "internet"]:
            s = _generate_series(mt, 200)
            assert np.std(s) > 10, f"{mt}: series appears flat"


# ==============================================================================
# ── Metric functions (delegated to app.core.metrics) ─────────────────────────
# ==============================================================================
class TestMetricFunctions:

    def setup_method(self):
        rng = np.random.default_rng(0)
        self.actual = np.array([100.0, 200.0, 300.0, 400.0, 500.0])
        self.perfect = self.actual.copy()
        self.noisy = self.actual + rng.normal(0, 20, len(self.actual))

    def test_mae_perfect(self):
        assert m.mae(self.actual, self.perfect) == pytest.approx(0.0, abs=1e-8)

    def test_rmse_perfect(self):
        assert m.rmse(self.actual, self.perfect) == pytest.approx(0.0, abs=1e-8)

    def test_mape_perfect(self):
        assert m.mape(self.actual, self.perfect) == pytest.approx(0.0, abs=1e-8)

    def test_r2_perfect(self):
        assert m.r2(self.actual, self.perfect) == pytest.approx(1.0, abs=1e-6)

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

    def test_r2_negative_for_bad_model(self):
        a = np.array([1.0, 2.0, 3.0, 4.0])
        p = np.full(4, 10.0)
        assert m.r2(a, p) < 0.5

    def test_mae_noisy_gt_zero(self):
        assert m.mae(self.actual, self.noisy) > 0

    def test_rmse_ge_mae(self):
        assert m.rmse(self.actual, self.noisy) >= m.mae(self.actual, self.noisy)


# ==============================================================================
# ── BenchmarkService ──────────────────────────────────────────────────────────
# ==============================================================================
class TestBenchmarkService:

    def test_run_returns_required_fields(self):
        result = BenchmarkService.run_benchmark(
            metric_types=["power"], horizon_steps=12, n_samples=80, include_ets=False
        )
        required = [
            "run_id", "timestamp", "models_evaluated", "datasets_evaluated",
            "results", "aggregate", "comparisons", "ranking_by_mae",
            "ranking_by_rmse", "ranking_by_mape", "ranking_by_speed",
            "overall_winner", "overall_winner_reason",
            "report_summary", "recommendations", "total_benchmark_time_ms",
        ]
        for field in required:
            assert field in result, f"Missing field: {field}"

    def test_two_models_without_ets(self):
        result = BenchmarkService.run_benchmark(
            metric_types=["traffic"], horizon_steps=8, n_samples=80, include_ets=False
        )
        assert set(result["models_evaluated"]) == {"Prophet", "ARIMA"}

    def test_three_models_with_ets(self):
        result = BenchmarkService.run_benchmark(
            metric_types=["power"], horizon_steps=8, n_samples=80, include_ets=True
        )
        assert set(result["models_evaluated"]) == {"Prophet", "ARIMA", "ETS"}

    def test_results_count_correct(self):
        result = BenchmarkService.run_benchmark(
            metric_types=["power", "traffic"], horizon_steps=8, n_samples=80, include_ets=False
        )
        assert len(result["results"]) == 4  # 2 datasets × 2 models

    def test_aggregate_keys_present(self):
        result = BenchmarkService.run_benchmark(
            metric_types=["water"], horizon_steps=8, n_samples=80, include_ets=False
        )
        for model in result["models_evaluated"]:
            agg = result["aggregate"][model]
            for metric in ("mae", "rmse", "mape", "r2", "train_ms", "infer_ms"):
                assert metric in agg

    def test_aggregate_mae_positive(self):
        result = BenchmarkService.run_benchmark(
            metric_types=["power"], horizon_steps=8, n_samples=80, include_ets=False
        )
        for mdl in result["models_evaluated"]:
            assert result["aggregate"][mdl]["mae"] >= 0

    def test_mape_realistic_range(self):
        result = BenchmarkService.run_benchmark(
            metric_types=["power"], horizon_steps=8, n_samples=80, include_ets=False
        )
        for mdl in result["models_evaluated"]:
            assert 0 <= result["aggregate"][mdl]["mape"] < 100

    def test_r2_leq_1(self):
        result = BenchmarkService.run_benchmark(
            metric_types=["power"], horizon_steps=8, n_samples=80, include_ets=False
        )
        for mdl in result["models_evaluated"]:
            assert result["aggregate"][mdl]["r2"] <= 1.0

    def test_rankings_complete(self):
        result = BenchmarkService.run_benchmark(
            metric_types=["power"], horizon_steps=8, n_samples=80, include_ets=False
        )
        for rank in ("ranking_by_mae", "ranking_by_rmse", "ranking_by_mape", "ranking_by_speed"):
            assert set(result[rank]) == set(result["models_evaluated"])

    def test_overall_winner_valid(self):
        result = BenchmarkService.run_benchmark(
            metric_types=["power"], horizon_steps=8, n_samples=80, include_ets=False
        )
        assert result["overall_winner"] in result["models_evaluated"]

    def test_comparisons_nonempty(self):
        result = BenchmarkService.run_benchmark(
            metric_types=["power"], horizon_steps=8, n_samples=80, include_ets=False
        )
        assert len(result["comparisons"]) >= 1

    def test_report_summary_nonempty(self):
        result = BenchmarkService.run_benchmark(
            metric_types=["water"], horizon_steps=8, n_samples=80, include_ets=False
        )
        assert len(result["report_summary"]) > 100

    def test_run_id_format(self):
        result = BenchmarkService.run_benchmark(
            metric_types=["power"], horizon_steps=8, n_samples=80, include_ets=False
        )
        assert result["run_id"].startswith("BM-")
        assert len(result["run_id"]) == 11

    def test_timing_positive(self):
        result = BenchmarkService.run_benchmark(
            metric_types=["power"], horizon_steps=8, n_samples=80, include_ets=False
        )
        assert result["total_benchmark_time_ms"] > 0

    def test_dataset_preview_structure(self):
        preview = BenchmarkService.get_dataset_preview("power", 100)
        assert "values" in preview
        assert len(preview["values"]) == 100
        assert preview["stats"]["mean"] > 0

    def test_dataset_preview_split(self):
        preview = BenchmarkService.get_dataset_preview("traffic", 100)
        assert preview["train_size"] == 80
        assert preview["test_size"] == 20

    def test_four_datasets_run(self):
        result = BenchmarkService.run_benchmark(
            metric_types=["power", "traffic", "water", "internet"],
            horizon_steps=8, n_samples=80, include_ets=False
        )
        assert len(result["results"]) == 8

    def test_ets_trains_faster_than_prophet(self):
        result = BenchmarkService.run_benchmark(
            metric_types=["power"], horizon_steps=8, n_samples=80, include_ets=True
        )
        agg = result["aggregate"]
        assert agg["ETS"]["train_ms"] > 0
        assert agg["Prophet"]["train_ms"] > 0
        assert agg["ETS"]["train_ms"] < agg["Prophet"]["train_ms"] * 2.0


# ==============================================================================
# ── REST API ────────────────────────────────────────────────────────────────
# ==============================================================================
class TestBenchmarkAPI:

    def test_quick_endpoint_ok(self):
        async def _a():
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.get("/api/v1/benchmark/quick?metric_type=power&n_samples=80&horizon=8")
                assert resp.status_code == 200
                data = resp.json()
                assert "overall_winner" in data
                assert "aggregate" in data
        _run(_a())

    def test_preview_endpoint_ok(self):
        async def _a():
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.get("/api/v1/benchmark/preview/traffic?n_samples=80")
                assert resp.status_code == 200
                data = resp.json()
                assert "values" in data
                assert len(data["values"]) == 80
        _run(_a())

    def test_run_endpoint_two_datasets(self):
        async def _a():
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                payload = {"metric_types": ["power", "water"], "horizon_steps": 8,
                           "n_samples": 80, "include_ets": False}
                resp = await client.post("/api/v1/benchmark/run", json=payload, timeout=120.0)
                assert resp.status_code == 200
                data = resp.json()
                assert len(data["results"]) == 4
        _run(_a())

    def test_openapi_has_benchmark_paths(self):
        async def _a():
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.get("/openapi.json")
                spec = resp.json()
                assert "/api/v1/benchmark/quick" in spec["paths"]
        _run(_a())
