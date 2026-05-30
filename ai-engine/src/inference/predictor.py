import time
import numpy as np
import logging
from typing import Dict, Any, Tuple
from src.config import ai_settings
from src.models.anomaly_detector import AnomalyDetectorManager
from src.ml.registry import ModelRegistryManager
from src.utils.ai_logger import ai_logger

logging.basicConfig(
    level=logging.INFO, format="[%(asctime)s] [%(levelname)s] [%(name)s] - %(message)s"
)
logger = logging.getLogger("predictor")


class RealTimePredictor:
    """
    Real-time sequence scoring engine. Consumes incoming telemetry feeds,
    performs anomaly evaluation using TorchScript optimized models,
    logs structural transaction records, and interfaces with the Model Registry.
    """

    def __init__(self, registry_dir: str = None):
        self.registry = (
            ModelRegistryManager(registry_dir=registry_dir)
            if registry_dir
            else ModelRegistryManager()
        )
        self.manager = AnomalyDetectorManager()

        # Attempt to load the promoted PRODUCTION model from registry
        loaded = False
        try:
            production_checkpoint = self.registry.get_tier_checkpoint("PRODUCTION")
            if production_checkpoint:
                self.manager.load(production_checkpoint)
                logger.info(
                    f"Successfully loaded PRODUCTION checkpoint: {production_checkpoint}"
                )
                loaded = True
        except Exception as e:
            logger.warning(
                f"Failed to load PRODUCTION model from registry: {e}. Falling back to default loader..."
            )

        if not loaded:
            try:
                self.manager.load_model()
                logger.info(
                    "Latest model weights successfully active from standard checkpoint."
                )
            except FileNotFoundError:
                logger.warning(
                    "No custom model registry found. Falling back on randomly initialized baseline for demonstration."
                )

    def analyze_sequence(
        self, sequence: np.ndarray, metric_name: str = "System_Metrics"
    ) -> Dict[str, Any]:
        """
        Processes a single sliding temporal sequence and scores it for anomalies.

        Args:
            sequence: array of shape (sequence_length, feature_dim)
            metric_name: label of the metric group being evaluated

        Returns:
            Dictionary containing evaluation metadata, flags, and scoring.
        """
        start_time = time.time()

        # Verify shape integrity
        expected_shape = (self.manager.sequence_length, self.manager.feature_dim)
        if sequence.shape != expected_shape:
            # Resize or pad sequence to match model configuration
            logger.warning(
                f"Data sequence shape {sequence.shape} does not match target model input configuration {expected_shape}. Formatting..."
            )
            sequence = np.resize(sequence, expected_shape)

        # Get reconstruction score (MSE) using JIT-optimized inference
        scores = self.manager.calculate_reconstruction_error(sequence)
        anomaly_score = float(scores[0])

        # Threshold comparison
        is_anomaly = anomaly_score > self.manager.anomaly_threshold
        severity = "INFO"
        if is_anomaly:
            severity = (
                "CRITICAL"
                if anomaly_score > (self.manager.anomaly_threshold * 1.2)
                else "WARNING"
            )

        latency_ms = (time.time() - start_time) * 1000

        # Log prediction transaction via centralized structured logger
        ai_logger.log_inference(
            metric_name=metric_name,
            anomaly_score=anomaly_score,
            latency_ms=latency_ms,
            is_anomaly=is_anomaly,
            severity=severity,
            threshold=self.manager.anomaly_threshold,
        )

        return {
            "metric_name": metric_name,
            "anomaly_score": anomaly_score,
            "threshold": self.manager.anomaly_threshold,
            "is_anomaly": is_anomaly,
            "severity": severity,
            "latency_ms": round(latency_ms, 3),
            "timestamp": time.time(),
        }


if __name__ == "__main__":
    logger.info(
        "Initializing production-grade anomaly scoring system for telemetry loop verification..."
    )
    predictor = RealTimePredictor()

    # Generate mock sequence (normal noise + random spike)
    mock_sequence = np.random.normal(
        0.0, 1.0, (ai_settings.SEQUENCE_LENGTH, ai_settings.FEATURE_DIMENSION)
    )

    # Run test inference
    result = predictor.analyze_sequence(
        mock_sequence, metric_name="Infrastructure_Telemetry"
    )
    logger.info(f"Inference run complete. Results: {result}")
