import logging
from typing import Tuple, List, Optional
import numpy as np
import pandas as pd
from src.config import ai_settings
from src.pipelines.preprocessing import TemporalPreprocessor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("data_pipeline")


class TemporalDataPipeline:
    """
    Handles preprocessing, sequence construction, and normalization
    for multi-dimensional time-series infrastructure logs.
    Integrated with the modular TemporalPreprocessor pipeline core.
    """

    def __init__(self, sequence_length: int = None):
        self.sequence_length = sequence_length or ai_settings.SEQUENCE_LENGTH
        self.preprocessor = TemporalPreprocessor()
        # Keep mean/std for backward-compatibility stubs
        self.mean: Optional[np.ndarray] = None
        self.std: Optional[np.ndarray] = None

    def fit_scaler(self, data: np.ndarray) -> None:
        """
        Calculates standardization weights based on training inputs (Z-score).
        """
        self.mean = np.mean(data, axis=0)
        self.std = np.std(data, axis=0)
        self.std[self.std == 0] = 1e-8

        # Fit inside our preprocessor too
        df_temp = pd.DataFrame(data, columns=[f"f{i}" for i in range(data.shape[1])])
        self.preprocessor.fit_scaler(
            df_temp, columns=df_temp.columns, strategy="standard"
        )
        logger.info(
            f"Scaler successfully calibrated. Mean dimensions: {self.mean.shape}"
        )

    def transform(self, data: np.ndarray) -> np.ndarray:
        """
        Applies z-score normalization on metrics.
        """
        if self.mean is None or self.std is None:
            raise ValueError("Scaler must be fit prior to running data transforms.")

        df_temp = pd.DataFrame(data, columns=[f"f{i}" for i in range(data.shape[1])])
        df_scaled = self.preprocessor.transform(df_temp, columns=df_temp.columns)
        return df_scaled.values

    def build_sliding_sequences(
        self, data: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Constructs overlapping sequences matching target lengths for temporal neural nets.
        """
        num_samples = len(data)
        if num_samples <= self.sequence_length:
            logger.warning(
                f"Insufficient data samples ({num_samples}) to assemble sequence length {self.sequence_length}."
            )
            return np.empty((0, self.sequence_length, data.shape[-1])), np.empty(
                (0, data.shape[-1])
            )

        sequences = []
        targets = []
        for i in range(num_samples - self.sequence_length):
            sequences.append(data[i : i + self.sequence_length])
            targets.append(data[i + self.sequence_length])

        return np.array(sequences), np.array(targets)

    def preprocess_raw_metrics(
        self, df: pd.DataFrame, feature_columns: List[str]
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        End-to-end processing pipeline using our advanced preprocessor framework.
        """
        logger.info(
            f"Ingesting raw metrics to preprocessing pipeline. Records: {len(df)}"
        )

        # 1. Clean missing values and outliers
        df_cleaned = df.copy()
        df_cleaned = self.preprocessor.handle_missing_values(
            df_cleaned, columns=feature_columns, strategy="linear"
        )
        df_cleaned = self.preprocessor.filter_outliers(
            df_cleaned, columns=feature_columns, strategy="iqr", action="clip"
        )

        # 2. Smooth data lines
        df_smoothed = self.preprocessor.smooth_data(
            df_cleaned, columns=feature_columns, strategy="ema", span=3
        )

        raw_values = df_smoothed[feature_columns].values

        # 3. Fit and apply scale transforms
        self.fit_scaler(raw_values)
        normalized = self.transform(raw_values)

        return self.build_sliding_sequences(normalized)
