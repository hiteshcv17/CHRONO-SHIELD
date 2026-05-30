import logging
from typing import List, Dict, Any, Union, Tuple, Optional
import numpy as np
import pandas as pd

logger = logging.getLogger("preprocessing")


class TemporalPreprocessor:
    """
    Production-grade temporal data preprocessing engine for ChronoShield AI.
    Features reusable stages for missing values, outlier filtration,
    timestamp resampling/alignment, moving average smoothing, and robust scaling.
    """

    def __init__(self):
        self.scalers: Dict[str, Dict[str, Any]] = {}

    def handle_missing_values(
        self,
        df: pd.DataFrame,
        columns: List[str],
        strategy: str = "time",
        limit: Optional[int] = None,
    ) -> pd.DataFrame:
        """
        Imputes missing values (NaN) across target columns.

        Args:
            df: Input pandas DataFrame
            columns: Target numeric columns to impute
            strategy: Imputation strategy - 'time' (time-weighted), 'linear', 'ffill', 'bfill', or 'mean'
            limit: Maximum consecutive NaNs to fill

        Returns:
            Preprocessed copy of the DataFrame
        """
        df_out = df.copy()

        for col in columns:
            if col not in df_out.columns:
                logger.warning(
                    f"Column '{col}' not found in DataFrame during missing value handling."
                )
                continue

            if strategy == "time":
                # Time interpolation requires a DatetimeIndex
                if isinstance(df_out.index, pd.DatetimeIndex):
                    df_out[col] = df_out[col].interpolate(method="time", limit=limit)
                else:
                    logger.warning(
                        "Index is not DatetimeIndex. Falling back to 'linear' interpolation."
                    )
                    df_out[col] = df_out[col].interpolate(method="linear", limit=limit)
            elif strategy == "linear":
                df_out[col] = df_out[col].interpolate(method="linear", limit=limit)
            elif strategy == "ffill":
                df_out[col] = df_out[col].ffill(limit=limit)
            elif strategy == "bfill":
                df_out[col] = df_out[col].bfill(limit=limit)
            elif strategy == "mean":
                mean_val = df_out[col].mean()
                df_out[col] = df_out[col].fillna(mean_val)
            else:
                raise ValueError(f"Unknown missing value strategy: {strategy}")

            # Safe double-pass fallback to clear remaining terminal NaNs
            df_out[col] = df_out[col].ffill().bfill()

        return df_out

    def filter_outliers(
        self,
        df: pd.DataFrame,
        columns: List[str],
        strategy: str = "iqr",
        factor: float = 1.5,
        action: str = "nan",
    ) -> pd.DataFrame:
        """
        Detects and filters mathematical outliers across telemetry streams.

        Args:
            df: Input pandas DataFrame
            columns: Target numeric columns
            strategy: Metric threshold strategy - 'iqr' (Interquartile Range) or 'zscore'
            factor: Outlier threshold boundary multiplier (e.g. 1.5 for IQR, 3.0 for Z-score)
            action: Response action - 'nan' (replace outlier with NaN) or 'clip' (caps outlier to limits)

        Returns:
            Preprocessed copy of the DataFrame
        """
        df_out = df.copy()

        for col in columns:
            if col not in df_out.columns:
                continue

            series = df_out[col]

            if strategy == "iqr":
                q1 = series.quantile(0.25)
                q3 = series.quantile(0.75)
                iqr = q3 - q1
                lower_bound = q1 - factor * iqr
                upper_bound = q3 + factor * iqr
            elif strategy == "zscore":
                mean = series.mean()
                std = series.std()
                if std == 0:
                    std = 1e-8
                lower_bound = mean - factor * std
                upper_bound = mean + factor * std
            else:
                raise ValueError(f"Unknown outlier detection strategy: {strategy}")

            if action == "nan":
                # Mark outliers as NaN (so they can be cleanly interpolated later)
                df_out.loc[(series < lower_bound) | (series > upper_bound), col] = (
                    np.nan
                )
            elif action == "clip":
                # Cap extreme values to the boundaries
                df_out[col] = np.clip(series, lower_bound, upper_bound)
            else:
                raise ValueError(f"Unknown outlier filter action: {action}")

        return df_out

    def align_timestamps(
        self,
        df: pd.DataFrame,
        timestamp_col: str,
        frequency: str = "5Min",
        aggregation: str = "mean",
    ) -> pd.DataFrame:
        """
        Aggregates duplicates and resamples irregular timestamps to a constant temporal frequency grid.

        Args:
            df: Input pandas DataFrame
            timestamp_col: Name of column containing timestamp series
            frequency: Output resampled pandas frequency string (e.g. '5Min', '1H')
            aggregation: Aggregation strategy for duplicate timestamps ('mean', 'max', 'min', 'first')

        Returns:
            DataFrame with DatetimeIndex aligned to frequency grid
        """
        df_out = df.copy()

        # 1. Parse timestamps and sort
        df_out[timestamp_col] = pd.to_datetime(df_out[timestamp_col])
        df_out = df_out.sort_values(by=timestamp_col)

        # 2. Deduplicate by aggregating matching timestamps
        non_time_cols = [c for c in df_out.columns if c != timestamp_col]
        df_dedup = df_out.groupby(timestamp_col)[non_time_cols].agg(aggregation)

        # 3. Resample to standard grid intervals
        df_resampled = df_dedup.resample(frequency).mean()

        # 4. Interpolate step gaps generated by resampling
        df_resampled = df_resampled.interpolate(method="time").ffill().bfill()

        return df_resampled

    def smooth_data(
        self,
        df: pd.DataFrame,
        columns: List[str],
        strategy: str = "ema",
        span: int = 5,
        window: int = 5,
    ) -> pd.DataFrame:
        """
        Applies smoothing filters to telemetry lines to clean sensor measurement noise.

        Args:
            df: Input pandas DataFrame
            columns: Target numeric columns to smooth
            strategy: Smoothing technique - 'ema' (Exponential Moving Average) or 'sma' (Simple Moving Average)
            span: Decay span parameter (for EMA)
            window: Rolling window duration steps (for SMA)

        Returns:
            Preprocessed copy of the DataFrame
        """
        df_out = df.copy()

        for col in columns:
            if col not in df_out.columns:
                continue

            if strategy == "ema":
                df_out[col] = df_out[col].ewm(span=span, adjust=False).mean()
            elif strategy == "sma":
                df_out[col] = df_out[col].rolling(window=window, min_periods=1).mean()
            else:
                raise ValueError(f"Unknown smoothing strategy: {strategy}")

        return df_out

    def fit_scaler(
        self, df: pd.DataFrame, columns: List[str], strategy: str = "standard"
    ) -> None:
        """
        Calculates and stores standard or robust scaling weights based on calibration data.

        Args:
            df: Calibration pandas DataFrame
            columns: Target columns to scale
            strategy: Scaling strategy - 'standard' (Z-score), 'minmax' (0 to 1), or 'robust' (median & IQR)
        """
        for col in columns:
            if col not in df.columns:
                continue

            series = df[col]
            params = {"strategy": strategy}

            if strategy == "standard":
                params["mean"] = float(series.mean())
                params["std"] = float(series.std())
                if params["std"] == 0:
                    params["std"] = 1e-8
            elif strategy == "minmax":
                params["min"] = float(series.min())
                params["max"] = float(series.max())
                diff = params["max"] - params["min"]
                params["diff"] = float(diff) if diff != 0 else 1e-8
            elif strategy == "robust":
                q1 = series.quantile(0.25)
                q3 = series.quantile(0.75)
                iqr = q3 - q1
                params["median"] = float(series.median())
                params["iqr"] = float(iqr) if iqr != 0 else 1e-8
            else:
                raise ValueError(f"Unknown scaling strategy: {strategy}")

            self.scalers[col] = params
            logger.info(f"Scaler calibrated for '{col}' using '{strategy}' strategy.")

    def transform(self, df: pd.DataFrame, columns: List[str]) -> pd.DataFrame:
        """
        Applies scaling transformations to target columns using pre-calibrated weights.

        Args:
            df: Input pandas DataFrame
            columns: Target columns to scale

        Returns:
            Transformed copy of the DataFrame
        """
        df_out = df.copy()

        for col in columns:
            if col not in df_out.columns:
                continue

            if col not in self.scalers:
                raise ValueError(f"Scaler has not been fit for column: {col}")

            params = self.scalers[col]
            strategy = params["strategy"]

            if strategy == "standard":
                df_out[col] = (df_out[col] - params["mean"]) / params["std"]
            elif strategy == "minmax":
                df_out[col] = (df_out[col] - params["min"]) / params["diff"]
            elif strategy == "robust":
                df_out[col] = (df_out[col] - params["median"]) / params["iqr"]

        return df_out

    def inverse_transform(self, df: pd.DataFrame, columns: List[str]) -> pd.DataFrame:
        """
        Reverses scaling transformations back to raw physical metrics.

        Args:
            df: Scaled pandas DataFrame
            columns: Target columns to reconstruct

        Returns:
            Reconstructed copy of the DataFrame
        """
        df_out = df.copy()

        for col in columns:
            if col not in df_out.columns:
                continue

            if col not in self.scalers:
                raise ValueError(f"Scaler has not been fit for column: {col}")

            params = self.scalers[col]
            strategy = params["strategy"]

            if strategy == "standard":
                df_out[col] = (df_out[col] * params["std"]) + params["mean"]
            elif strategy == "minmax":
                df_out[col] = (df_out[col] * params["diff"]) + params["min"]
            elif strategy == "robust":
                df_out[col] = (df_out[col] * params["iqr"]) + params["median"]

        return df_out

    def batch_preprocess(
        self,
        df: pd.DataFrame,
        feature_cols: List[str],
        timestamp_col: str,
        batch_size: int = 1000,
        frequency: str = "5Min",
        missing_strategy: str = "time",
        outlier_strategy: str = "iqr",
        scaling_strategy: str = "standard",
        smoothing_strategy: str = "ema",
    ) -> pd.DataFrame:
        """
        Preprocesses large telemetry streams using parallelizable, sequential batch frames.

        Args:
            df: Large raw pandas DataFrame
            feature_cols: Numeric metrics columns to preprocess
            timestamp_col: Timestamp column name
            batch_size: Row count chunk threshold for processing boundaries

        Returns:
            Unified preprocessed, aligned, and scaled DataFrame
        """
        if df.empty:
            return df

        chunks: List[pd.DataFrame] = []

        # Split DataFrame into consecutive processing chunks
        for i in range(0, len(df), batch_size):
            chunk = df.iloc[i : i + batch_size].copy()

            # Step 1. Align time-grid and aggregate duplicates
            chunk_aligned = self.align_timestamps(
                chunk, timestamp_col=timestamp_col, frequency=frequency
            )

            # Step 2. Remove and filter sensor noise anomalies
            chunk_filtered = self.filter_outliers(
                chunk_aligned,
                columns=feature_cols,
                strategy=outlier_strategy,
                action="nan",
            )

            # Step 3. Interpolate newly created outlier NaNs and original missing values
            chunk_imputed = self.handle_missing_values(
                chunk_filtered, columns=feature_cols, strategy=missing_strategy
            )

            # Step 4. Smooth sensor fluctuations
            chunk_smoothed = self.smooth_data(
                chunk_imputed, columns=feature_cols, strategy=smoothing_strategy
            )

            chunks.append(chunk_smoothed)

        if not chunks:
            return pd.DataFrame()

        # Concatenate aligned chunks and calibrate/apply scale transforms
        df_unified = pd.concat(chunks)

        # Eliminate any duplicate indices generated across boundary overlaps
        df_unified = df_unified.groupby(df_unified.index).mean()

        # Calibrate scaler and transform features
        self.fit_scaler(df_unified, columns=feature_cols, strategy=scaling_strategy)
        df_scaled = self.transform(df_unified, columns=feature_cols)

        return df_scaled
