# utils.py – Feature extraction and synthetic anomaly generation for ChronoShield AI

"""Utility module for the AI Engine.

Provides:
- `extract_features(df)` – Transform raw telemetry DataFrame into a feature matrix.
- `inject_synthetic_anomalies(df, anomaly_config, seed=None)` – Inject labeled synthetic anomalies.

The functions are deliberately lightweight and use only pandas, numpy and scikit‑learn utilities.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple

# ---------------------------------------------------------------------------
# Feature Extraction
# ---------------------------------------------------------------------------

def rolling_stats(series: pd.Series, window: int) -> Tuple[pd.Series, pd.Series]:
    """Return rolling mean and std for a pandas Series.

    Args:
        series: Input numeric series.
        window: Window size for rolling computation.
    Returns:
        (mean_series, std_series)
    """
    mean = series.rolling(window=window, min_periods=1).mean()
    std = series.rolling(window=window, min_periods=1).std().fillna(0)
    return mean, std


def extract_features(df: pd.DataFrame) -> pd.DataFrame:
    """Extract temporal features from raw telemetry.

    Expected columns: `timestamp` (datetime‑like) and one or more metric columns
    (e.g., `temperature`, `pressure`). The function adds:
    * Lag features for each metric (1, 2, 3 steps back).
    * Rolling mean / std with windows 3 and 7.
    * Simple Fourier magnitude for the first harmonic.
    """
    df = df.copy()
    # Ensure timestamp is datetime and sorted
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp")

    metric_cols = [c for c in df.columns if c not in {"timestamp"}]
    for col in metric_cols:
        # Lag features
        for lag in range(1, 4):
            df[f"{col}_lag_{lag}"] = df[col].shift(lag)
        # Rolling statistics
        for win in (3, 7):
            mean, std = rolling_stats(df[col], win)
            df[f"{col}_roll_mean_{win}"] = mean
            df[f"{col}_roll_std_{win}"] = std
        # Frequency domain – magnitude of first FFT component
        fft_vals = np.fft.fft(df[col].fillna(0).values)
        # Skip the zero‑frequency term, take magnitude of first harmonic
        df[f"{col}_fft_1_mag"] = np.abs(fft_vals[1])
    # Drop rows with NaNs introduced by lags
    df = df.dropna().reset_index(drop=True)
    return df

# ---------------------------------------------------------------------------
# Synthetic Anomaly Injection
# ---------------------------------------------------------------------------

def _inject_spike(series: pd.Series, magnitude: float, prob: float, rng: np.random.Generator) -> pd.Series:
    mask = rng.random(len(series)) < prob
    spike = rng.normal(loc=magnitude, scale=0.1 * magnitude, size=mask.sum())
    series.loc[mask] += spike
    return series


def _inject_drop(series: pd.Series, magnitude: float, prob: float, rng: np.random.Generator) -> pd.Series:
    mask = rng.random(len(series)) < prob
    drop = rng.normal(loc=-magnitude, scale=0.1 * magnitude, size=mask.sum())
    series.loc[mask] += drop
    return series


def _inject_noise(series: pd.Series, scale: float, prob: float, rng: np.random.Generator) -> pd.Series:
    mask = rng.random(len(series)) < prob
    noise = rng.normal(loc=0.0, scale=scale, size=mask.sum())
    series.loc[mask] += noise
    return series


def _inject_missing(series: pd.Series, prob: float, rng: np.random.Generator) -> pd.Series:
    mask = rng.random(len(series)) < prob
    series.loc[mask] = np.nan
    return series


def inject_synthetic_anomalies(
    df: pd.DataFrame,
    anomaly_config: Dict[str, Dict],
    seed: int | None = None,
) -> Tuple[pd.DataFrame, pd.Series]:
    """Inject synthetic anomalies into a telemetry DataFrame.

    Args:
        df: Raw DataFrame with numeric metric columns.
        anomaly_config: Mapping of anomaly type to parameters, e.g.::

            {
                "spike": {"magnitude": 15, "prob": 0.01},
                "drop": {"magnitude": 10, "prob": 0.008},
                "noise": {"scale": 5, "prob": 0.02},
                "missing": {"prob": 0.005},
            }
        seed: Optional random seed for reproducibility.
    Returns:
        (augmented_df, labels) where ``labels`` is a binary Series (1 = anomaly).
    """
    rng = np.random.default_rng(seed)
    df = df.copy()
    labels = pd.Series(0, index=df.index)

    # Apply each configured anomaly type
    for typ, params in anomaly_config.items():
        for col in [c for c in df.columns if c != "timestamp"]:
            if typ == "spike":
                df[col] = _inject_spike(df[col], params["magnitude"], params["prob"], rng)
                labels.loc[df[col] != df[col].shift()] = 1
            elif typ == "drop":
                df[col] = _inject_drop(df[col], params["magnitude"], params["prob"], rng)
                labels.loc[df[col] != df[col].shift()] = 1
            elif typ == "noise":
                df[col] = _inject_noise(df[col], params["scale"], params["prob"], rng)
                labels.loc[df[col] != df[col].shift()] = 1
            elif typ == "missing":
                df[col] = _inject_missing(df[col], params["prob"], rng)
                # Missing values are also considered anomalies
                labels[df[col].isna()] = 1
            # Additional custom types can be added here
    # After injection, forward‑fill missing values for model compatibility
    df_filled = df.fillna(method="ffill").fillna(method="bfill")
    return df_filled, labels

# End of utils.py
