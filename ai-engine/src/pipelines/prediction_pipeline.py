import time
import logging
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, Any, List, Tuple
from src.pipelines.data_pipeline import TemporalDataPipeline
from src.models.anomaly_detector import AnomalyDetectorManager
from src.utils.ai_logger import ai_logger

logger = logging.getLogger("prediction_pipeline")


class PredictionPipeline:
    """
    Production-grade end-to-end predictive pipeline.
    Encapsulates ingestion, imputation, outlier filtration, robust scaling,
    sequence building, and real-time inference using TorchScript optimized models.
    """

    def __init__(self, model_manager: AnomalyDetectorManager = None):
        self.model_manager = model_manager or AnomalyDetectorManager()
        self.data_pipeline = TemporalDataPipeline(
            sequence_length=self.model_manager.sequence_length
        )

    def fit(self, df: pd.DataFrame, feature_columns: List[str]) -> "PredictionPipeline":
        """
        Calibrate the preprocessing scaler on historical training data.
        """
        logger.info(f"Calibrating prediction pipeline scaler on {len(df)} samples...")
        df_cleaned = df[feature_columns].copy()
        df_cleaned = self.data_pipeline.preprocessor.handle_missing_values(
            df_cleaned, columns=feature_columns, strategy="linear"
        )
        df_cleaned = self.data_pipeline.preprocessor.filter_outliers(
            df_cleaned, columns=feature_columns, strategy="iqr", action="clip"
        )
        df_smoothed = self.data_pipeline.preprocessor.smooth_data(
            df_cleaned, columns=feature_columns, strategy="ema", span=3
        )

        raw_values = df_smoothed[feature_columns].values
        self.data_pipeline.fit_scaler(raw_values)
        return self

    def preprocess_and_score(
        self,
        df: pd.DataFrame,
        feature_columns: List[str],
        metric_name: str = "System_Metrics",
    ) -> List[Dict[str, Any]]:
        """
        Processes a raw input dataframe and computes anomaly scores/evaluations for each sequence.
        """
        if len(df) < self.model_manager.sequence_length:
            logger.warning(
                f"DataFrame row count ({len(df)}) is less than model sequence length requirement "
                f"({self.model_manager.sequence_length}). Cannot construct sequence."
            )
            return []

        # 1. Clean, smooth, and scale features
        df_cleaned = df.copy()
        df_cleaned = self.data_pipeline.preprocessor.handle_missing_values(
            df_cleaned, columns=feature_columns, strategy="linear"
        )
        df_cleaned = self.data_pipeline.preprocessor.filter_outliers(
            df_cleaned, columns=feature_columns, strategy="iqr", action="clip"
        )
        df_smoothed = self.data_pipeline.preprocessor.smooth_data(
            df_cleaned, columns=feature_columns, strategy="ema", span=3
        )

        raw_values = df_smoothed[feature_columns].values

        # Ensure scale parameters are fit, or fit them dynamically
        if self.data_pipeline.mean is None:
            logger.info(
                "Scaler not yet calibrated. Performing dynamic calibration on input data..."
            )
            self.data_pipeline.fit_scaler(raw_values)

        scaled_values = self.data_pipeline.transform(raw_values)

        # 2. Build sequence tensors
        sequences, _ = self.data_pipeline.build_sliding_sequences(scaled_values)
        if len(sequences) == 0:
            return []

        # 3. Perform optimized JIT inference & record telemetry logs
        results = []
        for idx, seq in enumerate(sequences):
            start_time = time.time()

            # Predict using optimized model (returns MSE reconstruction array)
            scores = self.model_manager.predict(seq)
            anomaly_score = float(scores[0])

            # Thresholding comparison
            is_anomaly = anomaly_score > self.model_manager.anomaly_threshold
            severity = "INFO"
            if is_anomaly:
                severity = (
                    "CRITICAL"
                    if anomaly_score > (self.model_manager.anomaly_threshold * 1.2)
                    else "WARNING"
                )

            latency_ms = (time.time() - start_time) * 1000

            # Centralized logging
            ai_logger.log_inference(
                metric_name=metric_name,
                anomaly_score=anomaly_score,
                latency_ms=latency_ms,
                is_anomaly=is_anomaly,
                severity=severity,
                threshold=self.model_manager.anomaly_threshold,
            )

            # Extract corresponding timestamp from df if available
            timestamp = time.time()
            if "timestamp" in df.columns:
                try:
                    ts_val = df.iloc[idx + self.model_manager.sequence_length][
                        "timestamp"
                    ]
                    if isinstance(ts_val, (pd.Timestamp, datetime)):
                        timestamp = ts_val.timestamp()
                    else:
                        timestamp = pd.to_datetime(ts_val).timestamp()
                except Exception:
                    pass

            results.append(
                {
                    "timestamp": timestamp,
                    "metric_name": metric_name,
                    "anomaly_score": anomaly_score,
                    "threshold": self.model_manager.anomaly_threshold,
                    "is_anomaly": is_anomaly,
                    "severity": severity,
                    "latency_ms": round(latency_ms, 3),
                }
            )

        return results
