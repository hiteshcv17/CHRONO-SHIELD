"""
Phase 29/30 — Forecasting Model Benchmarking Service (Refactored)
==================================================================
Orchestrates the full benchmark lifecycle using the core pipeline abstraction:

  1. Data generation   — synthetic time series per metric type
  2. Train/test split  — 80 / 20 chronological split
  3. Pipeline dispatch — via PipelineRegistry (Prophet | ARIMA | ETS)
  4. Metric computation — delegated to app.core.metrics
  5. Aggregation       — mean across datasets, rankings, comparisons
  6. Report generation — executive summary and recommendations

This service is a pure orchestrator: it has NO inline model code.
All model logic lives in app/core/pipeline.py.
All metric logic lives in app/core/metrics.py.
"""
import uuid
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

import numpy as np

from app.core import metrics as m
from app.core.registry import PipelineRegistry

logger = logging.getLogger("benchmark_service")

# ==============================================================================
# ── Dataset configuration ─────────────────────────────────────────────────────
# ==============================================================================
_DATASET_CONFIGS: Dict[str, Dict[str, Any]] = {
    "power": {
        "description": "Hourly electricity demand (MW) — diurnal + weekly seasonality",
        "base": 2800.0, "amplitude": 650.0, "trend": 0.35, "noise_std": 55.0,
        "seasonality_period": 24, "peaks": [8, 19], "peak_boosts": [220.0, 190.0],
    },
    "traffic": {
        "description": "Hourly vehicle count (vehicles/h) — AM/PM bimodal pattern",
        "base": 1600.0, "amplitude": 480.0, "trend": 0.15, "noise_std": 95.0,
        "seasonality_period": 24, "peaks": [8, 17], "peak_boosts": [320.0, 280.0],
    },
    "water": {
        "description": "Hourly water flow (m³/h) — residential usage curve",
        "base": 420.0, "amplitude": 120.0, "trend": 0.05, "noise_std": 18.0,
        "seasonality_period": 24, "peaks": [7, 20], "peak_boosts": [80.0, 65.0],
    },
    "internet": {
        "description": "Hourly network bandwidth (Mbps) — business hours + evening streaming",
        "base": 980.0, "amplitude": 310.0, "trend": 0.80, "noise_std": 70.0,
        "seasonality_period": 24, "peaks": [10, 21], "peak_boosts": [210.0, 260.0],
    },
}


def _generate_series(metric_type: str, n_samples: int, seed: int = 42) -> np.ndarray:
    """Generate a realistic synthetic time series for a given metric type."""
    cfg = _DATASET_CONFIGS[metric_type]
    rng = np.random.default_rng(seed)
    t = np.arange(n_samples)

    trend    = cfg["trend"] * t
    period   = cfg["seasonality_period"]
    seasonal = cfg["amplitude"] * np.sin(2 * np.pi * t / period - np.pi / 2)
    weekly   = cfg["amplitude"] * 0.25 * np.sin(2 * np.pi * t / 168)

    peak_overlay = np.zeros(n_samples)
    for peak_h, boost in zip(cfg["peaks"], cfg["peak_boosts"]):
        for i in range(n_samples):
            hour_in_day = i % period
            dist = min(abs(hour_in_day - peak_h), period - abs(hour_in_day - peak_h))
            if dist <= 1.5:
                peak_overlay[i] += boost * np.exp(-0.5 * (dist / 1.5) ** 2)

    noise  = rng.normal(0, cfg["noise_std"], n_samples)
    series = cfg["base"] + trend + seasonal + weekly + peak_overlay + noise
    return np.clip(series, cfg["base"] * 0.25, cfg["base"] * 2.4).astype(np.float64)


# ==============================================================================
# ── BenchmarkService ──────────────────────────────────────────────────────────
# ==============================================================================
class BenchmarkService:
    """
    Orchestrates multi-model, multi-dataset benchmark runs.

    All model execution is delegated to PipelineRegistry.
    All metric computation is delegated to app.core.metrics.
    """

    @staticmethod
    def run_benchmark(
        metric_types: Optional[List[str]] = None,
        horizon_steps: int = 24,
        n_samples: int = 200,
        include_ets: bool = True,
        seed: int = 42,
    ) -> Dict[str, Any]:
        """
        Run the full benchmark: Prophet vs ARIMA (+ optionally ETS)
        across all requested metric types.

        Returns a BenchmarkRun-compatible dict.
        """
        if metric_types is None:
            metric_types = ["power", "traffic", "water", "internet"]

        import time
        t_total = time.perf_counter()

        run_id    = f"BM-{uuid.uuid4().hex[:8].upper()}"
        timestamp = datetime.utcnow().isoformat()

        models_to_run = ["Prophet", "ARIMA"] + (["ETS"] if include_ets else [])
        results: List[Dict[str, Any]] = []

        for mtype in metric_types:
            cfg    = _DATASET_CONFIGS.get(mtype, _DATASET_CONFIGS["power"])
            series = _generate_series(mtype, n_samples, seed=seed)

            split_idx = int(len(series) * 0.8)
            train     = series[:split_idx]
            test      = series[split_idx:][:horizon_steps]
            horizon   = len(test)

            for model_name in models_to_run:
                # ── Build and run pipeline via registry ───────────────
                kwargs: Dict[str, Any] = {}
                if model_name == "ETS":
                    kwargs["seasonal_periods"] = cfg["seasonality_period"]

                try:
                    pipeline = PipelineRegistry.get(model_name, **kwargs)
                    run = pipeline.run(train, test)
                except Exception as e:
                    logger.error(f"Pipeline {model_name} failed on {mtype}: {e}")
                    run = {
                        "model_name": model_name,
                        "predicted": np.full(horizon, np.mean(train)),
                        "training_time_ms": 0.0,
                        "inference_time_ms": 0.0,
                        "total_time_ms": 0.0,
                        "converged": False,
                        "error_message": str(e)[:200],
                    }

                pred   = run["predicted"]
                actual = test[:len(pred)]

                # ── Compute metrics via core.metrics ──────────────────
                metric_vals = m.compute_all(actual, pred)

                results.append({
                    "model_name":        model_name,
                    "dataset_name":      f"{mtype.title()} Infrastructure",
                    "metric_type":       mtype,
                    "mae":               metric_vals["mae"],
                    "rmse":              metric_vals["rmse"],
                    "mape":              metric_vals["mape"],
                    "r2_score":          metric_vals["r2"],
                    "training_time_ms":  run["training_time_ms"],
                    "inference_time_ms": run["inference_time_ms"],
                    "total_time_ms":     run["total_time_ms"],
                    "n_train":           len(train),
                    "n_test":            horizon,
                    "horizon_steps":     horizon,
                    "converged":         run["converged"],
                    "error_message":     run["error_message"],
                })

        # ── Aggregate per model ────────────────────────────────────────────
        agg_lists: Dict[str, Dict[str, List[float]]] = {
            mdl: {"mae": [], "rmse": [], "mape": [], "r2": [], "train_ms": [], "infer_ms": []}
            for mdl in models_to_run
        }
        for r in results:
            mdl = r["model_name"]
            agg_lists[mdl]["mae"].append(r["mae"])
            agg_lists[mdl]["rmse"].append(r["rmse"])
            agg_lists[mdl]["mape"].append(r["mape"])
            agg_lists[mdl]["r2"].append(r["r2_score"])
            agg_lists[mdl]["train_ms"].append(r["training_time_ms"])
            agg_lists[mdl]["infer_ms"].append(r["inference_time_ms"])

        aggregate: Dict[str, Dict[str, float]] = {}
        for mdl, vals in agg_lists.items():
            train_ms = float(np.mean(vals["train_ms"]))
            infer_ms = float(np.mean(vals["infer_ms"]))
            aggregate[mdl] = {
                "mae":      round(float(np.mean(vals["mae"])),  4),
                "rmse":     round(float(np.mean(vals["rmse"])), 4),
                "mape":     round(float(np.mean(vals["mape"])), 4),
                "r2":       round(float(np.mean(vals["r2"])),   4),
                "train_ms": round(train_ms, 2),
                "infer_ms": round(infer_ms, 2),
                "total_ms": round(train_ms + infer_ms, 2),
            }

        # ── Rankings ──────────────────────────────────────────────────────
        def _rank(metric: str, lower_is_better: bool = True) -> List[str]:
            return sorted(
                models_to_run,
                key=lambda mdl: aggregate[mdl].get(metric, 9999),
                reverse=not lower_is_better,
            )

        rank_mae   = _rank("mae")
        rank_rmse  = _rank("rmse")
        rank_mape  = _rank("mape")
        rank_speed = _rank("total_ms")

        # ── Head-to-head comparisons ──────────────────────────────────────
        comparisons: List[Dict[str, Any]] = []
        model_pairs = [("Prophet", "ARIMA")]
        if include_ets:
            model_pairs += [("Prophet", "ETS"), ("ARIMA", "ETS")]

        for m_a, m_b in model_pairs:
            for metric in ("mae", "rmse", "mape"):
                v_a = aggregate[m_a][metric]
                v_b = aggregate[m_b][metric]
                if v_a <= v_b:
                    winner, loser, vw, vl = m_a, m_b, v_a, v_b
                else:
                    winner, loser, vw, vl = m_b, m_a, v_b, v_a
                improvement = ((vl - vw) / vl * 100) if vl > 1e-9 else 0.0
                comparisons.append({
                    "winner":         winner,
                    "loser":          loser,
                    "metric_name":    metric,
                    "winner_value":   round(vw, 4),
                    "loser_value":    round(vl, 4),
                    "improvement_pct": round(improvement, 2),
                    "is_significant": improvement > 5.0,
                })

        # ── Overall winner ────────────────────────────────────────────────
        rank_scores: Dict[str, float] = {mdl: 0.0 for mdl in models_to_run}
        for rank_list in [rank_mae, rank_rmse, rank_mape]:
            for pos, mdl in enumerate(rank_list):
                rank_scores[mdl] += pos
        for pos, mdl in enumerate(rank_speed):
            rank_scores[mdl] += pos * 0.5

        overall_winner = min(rank_scores, key=rank_scores.get)

        # ── Report ────────────────────────────────────────────────────────
        w_agg = aggregate[overall_winner]
        p_agg = aggregate.get("Prophet", {})
        a_agg = aggregate.get("ARIMA", {})

        mae_delta   = abs(p_agg.get("mae", 0) - a_agg.get("mae", 0))
        speed_ratio = a_agg.get("total_ms", 1) / max(p_agg.get("total_ms", 1), 0.1)

        report_summary = (
            f"Benchmark Run {run_id} — {len(metric_types)} infrastructure datasets "
            f"× {len(models_to_run)} models\n\n"
            f"OVERALL WINNER: {overall_winner}\n"
            f"  · Average MAE:  {w_agg['mae']:.2f}\n"
            f"  · Average RMSE: {w_agg['rmse']:.2f}\n"
            f"  · Average MAPE: {w_agg['mape']:.2f}%\n"
            f"  · Avg R² Score: {w_agg['r2']:.4f}\n\n"
            f"PROPHET vs ARIMA:\n"
            f"  · MAE difference: {mae_delta:.2f} units — "
            f"{'Prophet is more accurate' if p_agg.get('mae', 9e9) < a_agg.get('mae', 9e9) else 'ARIMA is more accurate'}\n"
            f"  · Speed ratio: ARIMA is {speed_ratio:.1f}× "
            f"{'faster' if speed_ratio < 1 else 'slower'} than Prophet\n"
            f"  · Prophet captures seasonality and trends more robustly\n"
            f"  · ARIMA is preferred when training latency is a hard constraint\n\n"
            f"DATASETS: {', '.join(t.title() for t in metric_types)}\n"
            f"HORIZON: {horizon_steps} steps | "
            f"TRAIN SIZE: ~{int(n_samples * 0.8)} | TEST SIZE: ~{horizon_steps}"
        )

        recommendations = [
            f"Deploy {overall_winner} for production forecasting — lowest composite error",
            f"Use ARIMA for real-time edge inference where <200ms training latency is required "
            f"(avg: {a_agg.get('train_ms', 0):.0f}ms)",
            "Prophet is recommended for datasets with strong daily and weekly seasonality",
            "ETS provides a fast statistical baseline for anomaly detection thresholding",
            "Retrain models weekly on fresh data to prevent concept drift",
            "For MAPE > 10%, consider ensemble averaging Prophet + ARIMA to reduce variance",
        ]

        return {
            "run_id":             run_id,
            "timestamp":          timestamp,
            "models_evaluated":   models_to_run,
            "datasets_evaluated": [_DATASET_CONFIGS[mt]["description"].split(" — ")[0] for mt in metric_types],
            "results":            results,
            "aggregate":          aggregate,
            "comparisons":        comparisons,
            "ranking_by_mae":     rank_mae,
            "ranking_by_rmse":    rank_rmse,
            "ranking_by_mape":    rank_mape,
            "ranking_by_speed":   rank_speed,
            "overall_winner":     overall_winner,
            "overall_winner_reason": (
                f"Lowest composite rank sum across MAE, RMSE, MAPE, and speed "
                f"({rank_scores[overall_winner]:.1f} pts)"
            ),
            "report_summary":     report_summary,
            "recommendations":    recommendations,
            "total_benchmark_time_ms": round((time.perf_counter() - t_total) * 1000, 2),
        }

    @staticmethod
    def get_dataset_preview(metric_type: str, n_samples: int = 200) -> Dict[str, Any]:
        """Return raw series values and config metadata for a dataset preview."""
        cfg    = _DATASET_CONFIGS.get(metric_type, _DATASET_CONFIGS["power"])
        series = _generate_series(metric_type, n_samples)
        split  = int(len(series) * 0.8)
        return {
            "metric_type":        metric_type,
            "description":        cfg["description"],
            "n_samples":          n_samples,
            "train_size":         split,
            "test_size":          n_samples - split,
            "seasonality_period": cfg["seasonality_period"],
            "values":             series.tolist(),
            "train_values":       series[:split].tolist(),
            "test_values":        series[split:].tolist(),
            "stats": {
                "mean": round(float(np.mean(series)), 2),
                "std":  round(float(np.std(series)),  2),
                "min":  round(float(np.min(series)),  2),
                "max":  round(float(np.max(series)),  2),
            },
        }
