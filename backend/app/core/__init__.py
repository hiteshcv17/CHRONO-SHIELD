"""
app/core — ChronoShield AI shared infrastructure layer.

Exports:
  metrics   — canonical error metrics (MAE, RMSE, MAPE, R²)
  pipeline  — ForecastingPipeline ABC + concrete Prophet/ARIMA/ETS pipelines
  registry  — PipelineRegistry for decoupled model selection
  base      — standardized API response envelopes and pagination
"""

from app.core import metrics, pipeline, registry, base  # noqa: F401
