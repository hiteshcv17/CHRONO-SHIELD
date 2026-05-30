import unittest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from src.models.statistical_detector import StatisticalAnomalyDetector


class TestStatisticalAnomalyDetector(unittest.TestCase):
    """
    Unit tests verifying the mathematical calculations and anomaly logging
    capabilities of the StatisticalAnomalyDetector class.
    """

    def setUp(self):
        # Construct baseline series
        base_time = datetime.utcnow()
        self.timestamps = [base_time + timedelta(minutes=i) for i in range(30)]
        
        # 30 ticks of normal noise around 50.0, plus 1 extreme outlier spike at index 25
        self.values = [50.0 + float(np.random.normal(0, 1)) for _ in range(30)]
        self.values[25] = 100.0  # Anomaly Spike!
        
        self.df = pd.DataFrame({
            "timestamp": self.timestamps,
            "metric_val": self.values
        })

    def test_calculate_rolling_stats(self):
        """Verify rolling stats are calculated correctly."""
        series = pd.Series([10.0, 10.0, 10.0, 10.0])
        mean, std = StatisticalAnomalyDetector.calculate_rolling_stats(series, window=3)
        
        # Mean of constants is constant
        self.assertAlmostEqual(mean.iloc[3], 10.0)
        # Standard deviation of constants is zero
        self.assertAlmostEqual(std.iloc[3], 0.0)

    def test_z_score_calculation(self):
        """Verify z-score calculations handle zero standard deviation safely."""
        series = pd.Series([10.0, 10.0, 10.0])
        mean, std = StatisticalAnomalyDetector.calculate_rolling_stats(series, window=3)
        z_scores = StatisticalAnomalyDetector.calculate_z_scores(series, mean, std)
        
        # Zero std shouldn't crash with division by zero
        self.assertEqual(len(z_scores), 3)
        self.assertFalse(np.isnan(z_scores.iloc[2]))
        self.assertFalse(np.isinf(z_scores.iloc[2]))

    def test_detect_anomalies_spike(self):
        """Verify that the outlier spike is correctly flagged as an anomaly."""
        anomalies = StatisticalAnomalyDetector.detect_anomalies(
            df=self.df,
            value_col="metric_val",
            timestamp_col="timestamp",
            window=20,
            z_threshold=3.0,
            metric_label="Test Metric"
        )
        
        # Ensure our spike at index 25 was detected
        self.assertGreaterEqual(len(anomalies), 1)
        
        # Inspect anomaly details
        anomaly = anomalies[0]
        self.assertEqual(anomaly["metric_name"], "Test Metric")
        self.assertEqual(anomaly["severity"], "CRITICAL")  # Large z-score deviation (from 50 to 100 is >10 stddev)
        self.assertGreaterEqual(anomaly["score"], 0.8)
        self.assertIn("Test Metric spiked to 100.0", anomaly["description"])

    def test_empty_dataframe(self):
        """Verify empty datasets gracefully return no anomalies."""
        empty_df = pd.DataFrame(columns=["timestamp", "metric_val"])
        anomalies = StatisticalAnomalyDetector.detect_anomalies(
            df=empty_df,
            value_col="metric_val",
            timestamp_col="timestamp"
        )
        self.assertEqual(len(anomalies), 0)
