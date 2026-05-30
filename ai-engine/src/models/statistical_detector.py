import numpy as np
import pandas as pd
import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from src.models.base import BaseModel

logger = logging.getLogger("statistical_detector")


class StatisticalAnomalyDetector(BaseModel):
    """
    Stateless statistical anomaly detection engine.
    Computes rolling statistics (mean, std, z-score) over a configured window
    and flags points exceeding statistical thresholds.
    """

    def __init__(
        self,
        window: int = 20,
        z_threshold: float = 2.5,
        value_col: str = "metric_val",
        timestamp_col: str = "timestamp",
        metric_label: str = "Metric",
    ):
        self.window = window
        self.z_threshold = z_threshold
        self.value_col = value_col
        self.timestamp_col = timestamp_col
        self.metric_label = metric_label

    def fit(self, X: Any, **kwargs: Any) -> Any:
        """
        Statistical detector is stateless/unsupervised, fit is a no-op.
        """
        logger.info("StatisticalAnomalyDetector.fit called (stateless model, no-op).")
        return self

    def predict(self, X: Any, **kwargs: Any) -> Any:
        """
        Perform inference and return the list of detected anomalies.
        Accepts a pandas DataFrame or a numpy array/list.
        """
        if not isinstance(X, pd.DataFrame):
            df = pd.DataFrame(X)
            # Find an appropriate column or use default value_col
            value_col = (
                self.value_col if self.value_col in df.columns else df.columns[0]
            )
            timestamp_col = (
                self.timestamp_col if self.timestamp_col in df.columns else "timestamp"
            )
            if timestamp_col not in df.columns:
                df[timestamp_col] = pd.date_range(
                    end=datetime.utcnow(), periods=len(df), freq="s"
                )
        else:
            df = X
            value_col = kwargs.get("value_col", self.value_col)
            timestamp_col = kwargs.get("timestamp_col", self.timestamp_col)

        window = kwargs.get("window", self.window)
        z_threshold = kwargs.get("z_threshold", self.z_threshold)
        metric_label = kwargs.get("metric_label", self.metric_label)

        return self.detect_anomalies(
            df=df,
            value_col=value_col,
            timestamp_col=timestamp_col,
            window=window,
            z_threshold=z_threshold,
            metric_label=metric_label,
        )

    def save(self, path: str, **kwargs: Any) -> str:
        """
        Save the detector configuration to a JSON file.
        """
        metadata = {
            "window": self.window,
            "z_threshold": self.z_threshold,
            "value_col": self.value_col,
            "timestamp_col": self.timestamp_col,
            "metric_label": self.metric_label,
        }
        with open(path, "w") as f:
            json.dump(metadata, f, indent=4)
        logger.info(f"StatisticalAnomalyDetector parameters saved to: {path}")
        return path

    def load(self, path: str, **kwargs: Any) -> None:
        """
        Load the detector configuration from a JSON file.
        """
        with open(path, "r") as f:
            metadata = json.load(f)
        self.window = metadata.get("window", self.window)
        self.z_threshold = metadata.get("z_threshold", self.z_threshold)
        self.value_col = metadata.get("value_col", self.value_col)
        self.timestamp_col = metadata.get("timestamp_col", self.timestamp_col)
        self.metric_label = metadata.get("metric_label", self.metric_label)
        logger.info(
            f"StatisticalAnomalyDetector parameters successfully loaded from: {path}"
        )

    @staticmethod
    def calculate_rolling_stats(
        series: pd.Series, window: int = 20
    ) -> tuple[pd.Series, pd.Series]:
        """
        Computes rolling mean and standard deviation.
        Uses min_periods=1 to compute stats even at the start of the window.
        """
        rolling_mean = series.rolling(window=window, min_periods=1).mean()
        rolling_std = series.rolling(window=window, min_periods=1).std()
        # Handle start of sequence or zero variance gracefully
        rolling_std = rolling_std.fillna(0.0)
        return rolling_mean, rolling_std

    @staticmethod
    def calculate_z_scores(
        series: pd.Series, rolling_mean: pd.Series, rolling_std: pd.Series
    ) -> pd.Series:
        """
        Computes z-scores for each point. Prevents division by zero.
        """
        # Small epsilon to prevent division by zero
        eps = 1e-6
        std_safe = rolling_std.copy()
        std_safe[std_safe < eps] = eps

        z_scores = (series - rolling_mean) / std_safe
        return z_scores

    @staticmethod
    def detect_anomalies(
        df: pd.DataFrame,
        value_col: str,
        timestamp_col: str,
        window: int = 20,
        z_threshold: float = 2.5,
        metric_label: str = "Metric",
    ) -> List[Dict[str, Any]]:
        """
        Computes rolling z-scores on the specified value column and returns detected anomalies.
        """
        if df.empty or value_col not in df.columns:
            return []

        # Ensure values are float/numeric
        values = pd.to_numeric(df[value_col], errors="coerce").fillna(0.0)

        # Parse timestamps properly
        if df[
            timestamp_col
        ].dtype == object or not pd.api.types.is_datetime64_any_dtype(
            df[timestamp_col]
        ):
            timestamps = pd.to_datetime(df[timestamp_col], errors="coerce")
        else:
            timestamps = df[timestamp_col]

        rolling_mean, rolling_std = StatisticalAnomalyDetector.calculate_rolling_stats(
            values, window
        )
        z_scores = StatisticalAnomalyDetector.calculate_z_scores(
            values, rolling_mean, rolling_std
        )

        anomalies = []
        for idx in range(len(df)):
            z = z_scores.iloc[idx]
            val = values.iloc[idx]
            ts = timestamps.iloc[idx]

            # If timestamp parsing failed, fallback to current time
            if pd.isnull(ts):
                ts = datetime.utcnow()

            if abs(z) > z_threshold:
                mean_val = rolling_mean.iloc[idx]
                std_val = rolling_std.iloc[idx]

                # Format explainable description
                direction = "spiked" if z > 0 else "dropped"
                desc = (
                    f"{metric_label} {direction} to {val:.1f}, which is {abs(z):.2f} "
                    f"standard deviations away from the {window}-period rolling average of {mean_val:.1f} "
                    f"(standard deviation: {std_val:.2f})."
                )

                # Severity classification
                if abs(z) > 3.5:
                    severity = "CRITICAL"
                elif abs(z) > 2.0:
                    severity = "WARNING"
                else:
                    severity = "INFO"

                # Anomaly score mapping: Cap the score mapping at z=5.0 for max score of 1.0
                score = min(1.0, abs(z) / 5.0)

                anomalies.append(
                    {
                        "id": f"anom-stat-{int(ts.timestamp())}-{value_col[:3].lower()}-{idx}",
                        "timestamp": ts,
                        "metric_name": f"{metric_label}",
                        "severity": severity,
                        "score": round(score, 3),
                        "description": desc,
                        "acknowledged": False,
                    }
                )

        return anomalies
