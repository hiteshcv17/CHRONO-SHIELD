import numpy as np
import pandas as pd
import pytest
from src.pipelines.preprocessing import TemporalPreprocessor


@pytest.fixture
def preprocessor():
    return TemporalPreprocessor()


@pytest.fixture
def sample_missing_df():
    data = {
        "timestamp": pd.date_range("2026-05-28 12:00:00", periods=5, freq="1Min"),
        "cpu": [10.0, np.nan, 30.0, np.nan, 50.0],
        "memory": [60.0, 70.0, np.nan, np.nan, 80.0]
    }
    df = pd.DataFrame(data)
    df.set_index("timestamp", inplace=True)
    return df


@pytest.fixture
def sample_outlier_df():
    data = {
        "timestamp": pd.date_range("2026-05-28 12:00:00", periods=10, freq="1Min"),
        "cpu": [20.0, 22.0, 21.0, 25.0, 500.0, 23.0, 24.0, -100.0, 22.0, 20.0]
    }
    df = pd.DataFrame(data)
    df.set_index("timestamp", inplace=True)
    return df


class TestTemporalPreprocessor:

    def test_handle_missing_values_linear(self, preprocessor, sample_missing_df):
        """Verify linear interpolation fills NaNs correctly."""
        df_filled = preprocessor.handle_missing_values(sample_missing_df, columns=["cpu", "memory"], strategy="linear")
        
        # NaNs should be completely resolved
        assert df_filled.isna().sum().sum() == 0
        
        # Specific linear interpolation values checks
        assert df_filled.loc["2026-05-28 12:01:00", "cpu"] == 20.0  # (10 + 30) / 2
        assert df_filled.loc["2026-05-28 12:03:00", "cpu"] == 40.0  # (30 + 50) / 2
        
        # Double gap interpolation checks for memory: index 2 and 3 should scale from 70 to 80
        assert df_filled.loc["2026-05-28 12:02:00", "memory"] == pytest.approx(73.33, abs=1e-1)
        assert df_filled.loc["2026-05-28 12:03:00", "memory"] == pytest.approx(76.67, abs=1e-1)

    def test_filter_outliers_iqr(self, preprocessor, sample_outlier_df):
        """Verify IQR outlier detection detects spikes and handles actions (NaN and Clip)."""
        # Strategy 'nan': Outliers should be marked as NaN
        df_nan = preprocessor.filter_outliers(sample_outlier_df, columns=["cpu"], strategy="iqr", factor=1.5, action="nan")
        assert np.isnan(df_nan.loc["2026-05-28 12:04:00", "cpu"])  # 500.0 is an outlier
        assert np.isnan(df_nan.loc["2026-05-28 12:07:00", "cpu"])  # -100.0 is an outlier
        assert df_nan.isna().sum()["cpu"] == 2
        
        # Strategy 'clip': Outliers should be capped at bounds
        df_clip = preprocessor.filter_outliers(sample_outlier_df, columns=["cpu"], strategy="iqr", factor=1.5, action="clip")
        assert df_clip.isna().sum()["cpu"] == 0
        assert df_clip.loc["2026-05-28 12:04:00", "cpu"] < 50.0  # Capped downwards
        assert df_clip.loc["2026-05-28 12:07:00", "cpu"] > 0.0   # Capped upwards

    def test_align_timestamps_resample(self, preprocessor):
        """Verify timestamp resampling aggregates duplicates and creates constant frequency grid."""
        # Create duplicate and irregular timestamps
        data = {
            "timestamp": [
                "2026-05-28 12:00:00",
                "2026-05-28 12:00:00",  # Duplicate
                "2026-05-28 12:02:00",
                "2026-05-28 12:04:00"   # Gap at 12:01 and 12:03
            ],
            "cpu": [10.0, 20.0, 30.0, 40.0]
        }
        df = pd.DataFrame(data)
        
        # Align to constant 1-minute grid frequency
        df_aligned = preprocessor.align_timestamps(df, timestamp_col="timestamp", frequency="1Min", aggregation="mean")
        
        # Verify index type and size
        assert isinstance(df_aligned.index, pd.DatetimeIndex)
        assert len(df_aligned) == 5  # 12:00, 12:01, 12:02, 12:03, 12:04
        
        # Verify duplicate aggregated (mean of 10 and 20 is 15)
        assert df_aligned.loc["2026-05-28 12:00:00", "cpu"] == 15.0
        
        # Verify gap interpolation filled (linear step between 15 and 30 is 22.5)
        assert df_aligned.loc["2026-05-28 12:01:00", "cpu"] == 22.5

    def test_smooth_data_filters(self, preprocessor):
        """Verify SMA and EMA smoothing metrics."""
        data = {
            "cpu": [10.0, 20.0, 10.0, 20.0, 10.0]
        }
        df = pd.DataFrame(data)
        
        # Exponential Moving Average smoothing
        df_ema = preprocessor.smooth_data(df, columns=["cpu"], strategy="ema", span=3)
        assert df_ema.loc[4, "cpu"] != df.loc[4, "cpu"]  # Value smoothed
        
        # Simple Moving Average smoothing
        df_sma = preprocessor.smooth_data(df, columns=["cpu"], strategy="sma", window=3)
        assert df_sma.loc[2, "cpu"] == pytest.approx(13.33, abs=1e-1)  # (10 + 20 + 10) / 3

    def test_scalers_calibrations(self, preprocessor):
        """Verify scale transformations and reverse reconstructions (Standard, MinMax, Robust)."""
        data = {
            "cpu": [10.0, 20.0, 30.0, 40.0, 50.0]
        }
        df = pd.DataFrame(data)
        
        # 1. Standard Scaling Check
        preprocessor.fit_scaler(df, columns=["cpu"], strategy="standard")
        df_std = preprocessor.transform(df, columns=["cpu"])
        assert df_std["cpu"].mean() == pytest.approx(0.0, abs=1e-7)
        
        # Verify reconstruction
        df_recon_std = preprocessor.inverse_transform(df_std, columns=["cpu"])
        assert np.allclose(df_recon_std["cpu"].values, df["cpu"].values)

        # 2. MinMax Scaling Check
        preprocessor.fit_scaler(df, columns=["cpu"], strategy="minmax")
        df_mm = preprocessor.transform(df, columns=["cpu"])
        assert df_mm["cpu"].min() == 0.0
        assert df_mm["cpu"].max() == 1.0
        
        df_recon_mm = preprocessor.inverse_transform(df_mm, columns=["cpu"])
        assert np.allclose(df_recon_mm["cpu"].values, df["cpu"].values)

        # 3. Robust Scaling Check
        preprocessor.fit_scaler(df, columns=["cpu"], strategy="robust")
        df_rob = preprocessor.transform(df, columns=["cpu"])
        assert df_rob["cpu"].median() == 0.0
        
        df_recon_rob = preprocessor.inverse_transform(df_rob, columns=["cpu"])
        assert np.allclose(df_recon_rob["cpu"].values, df["cpu"].values)

    def test_batch_preprocess_pipeline(self, preprocessor):
        """Verify batch_preprocess runs the full sequence seamlessly."""
        # Create a large noisy telemetry dataframe with duplicates and gaps
        data = {
            "timestamp": [
                "2026-05-28 12:00:00", "2026-05-28 12:00:00",
                "2026-05-28 12:02:00", "2026-05-28 12:03:00",
                "2026-05-28 12:05:00", "2026-05-28 12:06:00",
                "2026-05-28 12:08:00"
            ],
            "cpu": [10.0, 12.0, 15.0, 600.0, np.nan, 14.0, 16.0]  # 600 is outlier, NaN present
        }
        df = pd.DataFrame(data)
        
        df_proc = preprocessor.batch_preprocess(
            df,
            feature_cols=["cpu"],
            timestamp_col="timestamp",
            batch_size=4,
            frequency="1Min",
            scaling_strategy="standard"
        )
        
        # Assertions
        assert not df_proc.empty
        assert isinstance(df_proc.index, pd.DatetimeIndex)
        assert df_proc.isna().sum()["cpu"] == 0
        assert df_proc["cpu"].mean() == pytest.approx(0.0, abs=1e-2)
