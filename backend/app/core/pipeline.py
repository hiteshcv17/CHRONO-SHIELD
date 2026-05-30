"""
app/core/pipeline — Forecasting Pipeline Abstraction.

Defines the ForecastingPipeline ABC and three concrete implementations:
  ProphetPipeline  — Facebook Prophet (additive decomposition)
  ArimaPipeline    — ARIMA via statsmodels (autoregressive integrated)
  EtsPipeline      — Holt-Winters Exponential Smoothing

Each pipeline exposes a uniform interface:
  pipeline.fit(train)        → self
  pipeline.predict(horizon)  → np.ndarray
  pipeline.name              → str

This decouples model selection from benchmark orchestration and makes it
trivial to add new models by subclassing ForecastingPipeline.
"""
import time
import warnings
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Tuple
import numpy as np

warnings.filterwarnings("ignore")


# ==============================================================================
# Abstract base
# ==============================================================================
class ForecastingPipeline(ABC):
    """
    Abstract base class for all forecasting pipelines.

    Subclasses must implement `fit()` and `predict()`. The base class
    provides timing, error capture, and a standardised result dict.
    """

    #: Human-readable model name (e.g. "Prophet")
    name: str = "BasePipeline"

    def __init__(self) -> None:
        self._training_time_ms: float = 0.0
        self._inference_time_ms: float = 0.0
        self._converged: bool = False
        self._error_message: Optional[str] = None
        self._train: Optional[np.ndarray] = None

    # ── Abstract interface ────────────────────────────────────────────────
    @abstractmethod
    def _fit_impl(self, train: np.ndarray) -> None:
        """Internal fit implementation — must be overridden by subclasses."""

    @abstractmethod
    def _predict_impl(self, horizon: int) -> np.ndarray:
        """Internal predict implementation — must be overridden by subclasses."""

    # ── Public interface (adds timing + error handling) ───────────────────
    def fit(self, train: np.ndarray) -> "ForecastingPipeline":
        """Fit the model on training data, recording elapsed time."""
        self._train = train
        t0 = time.perf_counter()
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                self._fit_impl(train)
            self._converged = True
        except Exception as exc:
            self._converged = False
            self._error_message = str(exc)[:300]
        self._training_time_ms = (time.perf_counter() - t0) * 1000
        return self

    def predict(self, horizon: int) -> np.ndarray:
        """Generate `horizon` step-ahead forecasts, recording elapsed time."""
        t0 = time.perf_counter()
        try:
            if not self._converged or self._train is None:
                fallback_val = float(np.mean(self._train)) if self._train is not None else 0.0
                result = np.full(horizon, fallback_val)
            else:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    result = self._predict_impl(horizon)
            result = np.clip(result, 0.0, None)
        except Exception as exc:
            self._error_message = (self._error_message or "") + f" | predict: {exc}"
            fallback_val = float(np.mean(self._train)) if self._train is not None else 0.0
            result = np.full(horizon, fallback_val)
        self._inference_time_ms = (time.perf_counter() - t0) * 1000
        return result[:horizon]

    def run(self, train: np.ndarray, test: np.ndarray) -> Dict[str, Any]:
        """
        Convenience method: fit → predict → return standardised result dict.
        """
        t_total = time.perf_counter()
        self.fit(train)
        predicted = self.predict(len(test))
        return {
            "model_name": self.name,
            "predicted": predicted,
            "training_time_ms": round(self._training_time_ms, 2),
            "inference_time_ms": round(self._inference_time_ms, 2),
            "total_time_ms": round((time.perf_counter() - t_total) * 1000, 2),
            "converged": self._converged,
            "error_message": self._error_message,
        }


# ==============================================================================
# Concrete pipelines
# ==============================================================================
class ProphetPipeline(ForecastingPipeline):
    """Facebook Prophet — additive decomposition with changepoints."""

    name = "Prophet"

    def __init__(self) -> None:
        super().__init__()
        self._model = None
        self._train_len: int = 0

    def _fit_impl(self, train: np.ndarray) -> None:
        from prophet import Prophet
        import pandas as pd
        from datetime import datetime, timedelta

        self._train_len = len(train)
        base_dt = datetime(2026, 1, 1)
        dates = [base_dt + timedelta(hours=i) for i in range(len(train))]
        df = pd.DataFrame({"ds": dates, "y": train})

        self._model = Prophet(
            yearly_seasonality=False,
            weekly_seasonality=True,
            daily_seasonality=True,
            seasonality_mode="additive",
            changepoint_prior_scale=0.05,
        )
        self._model.fit(df)

    def _predict_impl(self, horizon: int) -> np.ndarray:
        import pandas as pd
        from datetime import datetime, timedelta

        base_dt = datetime(2026, 1, 1)
        future_dates = [
            base_dt + timedelta(hours=i + self._train_len)
            for i in range(horizon)
        ]
        future_df = pd.DataFrame({"ds": future_dates})
        forecast = self._model.predict(future_df)
        return forecast["yhat"].values[:horizon]


class ArimaPipeline(ForecastingPipeline):
    """ARIMA via statsmodels — falls back through simpler orders on failure."""

    name = "ARIMA"

    #: Default order to try first; pipeline auto-degrades on convergence failure
    DEFAULT_ORDER: Tuple[int, int, int] = (2, 1, 2)
    FALLBACK_ORDERS = [(1, 1, 1), (1, 1, 0), (0, 1, 1)]

    def __init__(self, order: Tuple[int, int, int] = DEFAULT_ORDER) -> None:
        super().__init__()
        self._order = order
        self._model_fit = None

    def _fit_impl(self, train: np.ndarray) -> None:
        from statsmodels.tsa.arima.model import ARIMA as _ARIMA

        for try_order in [self._order] + self.FALLBACK_ORDERS:
            try:
                result = _ARIMA(train, order=try_order).fit()
                self._model_fit = result
                return
            except Exception:
                continue
        raise RuntimeError("All ARIMA orders failed to converge")

    def _predict_impl(self, horizon: int) -> np.ndarray:
        return np.array(self._model_fit.forecast(steps=horizon))


class EtsPipeline(ForecastingPipeline):
    """Holt-Winters Exponential Smoothing — fast statistical baseline."""

    name = "ETS"

    def __init__(self, seasonal_periods: int = 24) -> None:
        super().__init__()
        self._seasonal_periods = seasonal_periods
        self._model_fit = None

    def _fit_impl(self, train: np.ndarray) -> None:
        from statsmodels.tsa.holtwinters import ExponentialSmoothing

        sp = min(self._seasonal_periods, len(train) // 2)
        try:
            m = ExponentialSmoothing(
                train, trend="add", seasonal="add", seasonal_periods=sp
            ).fit(optimized=True)
        except Exception:
            # Degrade to simple Holt (trend, no seasonality)
            m = ExponentialSmoothing(train, trend="add", seasonal=None).fit()
        self._model_fit = m

    def _predict_impl(self, horizon: int) -> np.ndarray:
        return np.array(self._model_fit.forecast(horizon))
