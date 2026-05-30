"""
app/core/metrics — Canonical forecast error metric functions.

Single source of truth for all accuracy measures used across the platform.
All functions are pure, stateless, and independently testable.
"""

import math
import numpy as np


# ==============================================================================
# Type alias
# ==============================================================================
Array = np.ndarray


def mae(actual: Array, predicted: Array) -> float:
    """
    Mean Absolute Error — average magnitude of prediction residuals.

    Lower is better. Scale-dependent (same units as the time series).
    """
    return float(np.mean(np.abs(actual - predicted)))


def rmse(actual: Array, predicted: Array) -> float:
    """
    Root Mean Square Error — penalises large errors more heavily than MAE.

    Lower is better. Scale-dependent.
    """
    return float(np.sqrt(np.mean((actual - predicted) ** 2)))


def mape(actual: Array, predicted: Array) -> float:
    """
    Mean Absolute Percentage Error — scale-independent accuracy measure.

    Lower is better. Returns a percentage (e.g. 5.2 means 5.2%).
    Zero values in `actual` are safely masked.
    """
    mask = np.abs(actual) > 1e-6
    if not mask.any():
        return 0.0
    return float(np.mean(np.abs((actual[mask] - predicted[mask]) / actual[mask])) * 100)


def r2(actual: Array, predicted: Array) -> float:
    """
    Coefficient of Determination (R²) — proportion of variance explained.

    Higher is better. Bounded [-∞, 1.0]. Returns 1.0 for perfectly flat series.
    """
    ss_res = float(np.sum((actual - predicted) ** 2))
    ss_tot = float(np.sum((actual - np.mean(actual)) ** 2))
    if ss_tot < 1e-10:
        return 1.0
    return 1.0 - ss_res / ss_tot


def compute_all(actual: Array, predicted: Array) -> dict:
    """
    Convenience wrapper — compute all four metrics in a single call.

    Returns:
        {
            "mae":  float,
            "rmse": float,
            "mape": float,
            "r2":   float,
        }
    """
    return {
        "mae": round(mae(actual, predicted), 4),
        "rmse": round(rmse(actual, predicted), 4),
        "mape": round(mape(actual, predicted), 4),
        "r2": round(r2(actual, predicted), 4),
    }
