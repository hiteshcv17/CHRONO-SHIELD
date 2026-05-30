"""
Phase 29 — Forecasting Model Benchmarking Framework
Pydantic schemas for model evaluation results, comparison reports, and metrics.
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel


class ModelMetrics(BaseModel):
    """Evaluation metrics for a single model on a single dataset."""
    model_name: str
    dataset_name: str
    metric_type: str            # power | traffic | water | internet

    # ── Accuracy metrics ────────────────────────────────────────────────
    mae: float                  # Mean Absolute Error
    rmse: float                 # Root Mean Square Error
    mape: float                 # Mean Absolute Percentage Error (%)
    r2_score: float             # Coefficient of Determination

    # ── Speed metrics ───────────────────────────────────────────────────
    training_time_ms: float
    inference_time_ms: float
    total_time_ms: float

    # ── Additional diagnostics ──────────────────────────────────────────
    n_train: int                # Training set size
    n_test: int                 # Test set size
    horizon_steps: int          # Forecast horizon (steps ahead)
    converged: bool             # Model converged without error
    error_message: Optional[str]


class BenchmarkDataset(BaseModel):
    """Metadata for a single benchmark dataset."""
    dataset_name: str
    metric_type: str
    n_samples: int
    train_size: int
    test_size: int
    seasonality_period: int
    trend_slope: float
    noise_std: float
    description: str


class ModelComparison(BaseModel):
    """
    Head-to-head comparison of two models on a specific metric.
    """
    winner: str                 # model name that won
    loser: str
    metric_name: str            # mae | rmse | mape
    winner_value: float
    loser_value: float
    improvement_pct: float      # % improvement winner has over loser
    is_significant: bool        # |improvement| > 5%


class BenchmarkRun(BaseModel):
    """
    Results for a single benchmark run across all models and datasets.
    """
    run_id: str
    timestamp: str
    models_evaluated: List[str]
    datasets_evaluated: List[str]

    # ── Per-model metrics (model_name → list of per-dataset metrics) ──
    results: List[ModelMetrics]

    # ── Aggregate metrics (mean across datasets) ───────────────────────
    aggregate: Dict[str, Dict[str, float]]   # model → {mae, rmse, mape, train_ms, infer_ms}

    # ── Head-to-head comparisons ──────────────────────────────────────
    comparisons: List[ModelComparison]

    # ── Rankings ──────────────────────────────────────────────────────
    ranking_by_mae: List[str]   # sorted model names, best first
    ranking_by_rmse: List[str]
    ranking_by_mape: List[str]
    ranking_by_speed: List[str] # fastest first

    overall_winner: str         # best across all criteria
    overall_winner_reason: str

    # ── Evaluation report ─────────────────────────────────────────────
    report_summary: str         # Multi-line executive summary
    recommendations: List[str]
    total_benchmark_time_ms: float


class BenchmarkRequest(BaseModel):
    metric_types: List[str] = ["power", "traffic", "water", "internet"]
    horizon_steps: int = 24
    n_samples: int = 200
    include_ets: bool = True    # Include Exponential Smoothing as 3rd model
