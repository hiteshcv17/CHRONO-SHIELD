import os
import json
import shutil
import tempfile
import unittest
import numpy as np
import pandas as pd
import torch
from datetime import datetime, timedelta

from src.models.base import BaseModel
from src.models.statistical_detector import StatisticalAnomalyDetector
from src.models.anomaly_detector import AnomalyDetectorManager, TemporalAutoencoder
from src.ml.registry import ModelRegistryManager
from src.utils.ai_logger import AISubsystemLogger
from src.pipelines.prediction_pipeline import PredictionPipeline
from src.inference.predictor import RealTimePredictor


class TestRefactoredAISubsystem(unittest.TestCase):
    """
    Production-grade verification suite for the refactored ChronoShield AI engine subsystem.
    """

    def setUp(self):
        # Create a temporary workspace for file checkpoints, registries and logs
        self.test_dir = tempfile.mkdtemp()
        self.registry_dir = os.path.join(self.test_dir, "registry")
        self.log_file = os.path.join(self.test_dir, "ml_telemetry.json")

    def tearDown(self):
        # Cleanup temporary workspace
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_polymorphism_and_inheritance(self):
        """Assert both detectors inherit from BaseModel and implement abstract interfaces."""
        # 1. Statistical Detector
        stat_detector = StatisticalAnomalyDetector()
        self.assertTrue(isinstance(stat_detector, BaseModel))

        # 2. PyTorch DL Detector
        dl_detector = AnomalyDetectorManager()
        self.assertTrue(isinstance(dl_detector, BaseModel))

    def test_statistical_detector_polymorphic_flow(self):
        """Verify the polymorphic fit/predict interface of StatisticalAnomalyDetector."""
        detector = StatisticalAnomalyDetector(window=30, z_threshold=2.0)
        
        # Mock historical series dataframe
        df = pd.DataFrame({
            "timestamp": pd.date_range(end=datetime.utcnow(), periods=40, freq="min"),
            "metric_val": [10.0] * 39 + [200.0]  # Outlier spike at the end (large enough for critical)
        })

        # Fit is stateless (no-op) but should execute without issues
        self.assertEqual(detector.fit(df), detector)

        # Polymorphic predict should correctly return anomalies list
        anomalies = detector.predict(df, value_col="metric_val", timestamp_col="timestamp")
        self.assertEqual(len(anomalies), 1)
        self.assertEqual(anomalies[0]["severity"], "CRITICAL")
        self.assertEqual(anomalies[0]["metric_name"], "Metric")

    def test_pytorch_detector_jit_compilation_and_inference(self):
        """Verify TemporalAutoencoder TorchScript compiler matching eager outputs."""
        manager = AnomalyDetectorManager()
        
        # Assert jit_model is compiled successfully
        self.assertIsNotNone(manager.jit_model)
        self.assertTrue(
            isinstance(manager.jit_model, torch.jit.ScriptModule) or
            isinstance(manager.jit_model, torch.nn.Module)
        )

        # Generate a dummy normal sequence sequence shape (1, sequence_length, feature_dim)
        seq = np.random.normal(0.0, 0.5, (1, manager.sequence_length, manager.feature_dim))
        
        # Standard model evaluation prediction
        manager.model.eval()
        with torch.no_grad():
            seq_t = torch.tensor(seq, dtype=torch.float32).to(manager.device)
            eager_output = manager.model(seq_t).cpu().numpy()

        # JIT compiled model evaluation prediction
        manager.jit_model.eval()
        with torch.no_grad():
            jit_output = manager.jit_model(seq_t).cpu().numpy()

        # Both output matrices must be mathematically identical
        np.testing.assert_allclose(eager_output, jit_output, rtol=1e-5, atol=1e-5)

        # Run polymorphic predict
        mse_scores = manager.predict(seq)
        self.assertEqual(mse_scores.shape, (1,))

    def test_pytorch_training_loop_fit(self):
        """Verify full unsupervised PyTorch model fitting and dynamic threshold recalculation."""
        manager = AnomalyDetectorManager()
        
        # Create normal sequences dataset shape (20, 60, 10)
        X_train = np.random.normal(0.0, 0.2, (20, manager.sequence_length, manager.feature_dim))
        
        # Fit model on training sequences
        old_threshold = manager.anomaly_threshold
        manager.fit(X_train, epochs=2, batch_size=4)
        
        # Verify threshold updated dynamically
        self.assertNotEqual(manager.anomaly_threshold, old_threshold)
        self.assertGreater(manager.anomaly_threshold, 0.0)

    def test_model_registry_lifecycle_and_rollbacks(self):
        """Verify the complete model checkpoint registration, promotion and rollback loops."""
        registry = ModelRegistryManager(registry_dir=self.registry_dir)

        # Create a mock checkpoint file path
        dummy_checkpoint = os.path.join(self.test_dir, "dummy_model.pth")
        torch.save({"dummy_state": [1, 2, 3]}, dummy_checkpoint)

        # 1. Register multiple versions of models
        m1 = registry.register_model(
            model_id="v1.0.0",
            checkpoint_path=dummy_checkpoint,
            parameters={"latent_dim": 8, "lr": 1e-3},
            metrics={"val_loss": 0.045}
        )
        self.assertEqual(m1["model_id"], "v1.0.0")
        self.assertTrue(os.path.exists(m1["checkpoint_path"]))

        m2 = registry.register_model(
            model_id="v1.1.0_challenger",
            checkpoint_path=dummy_checkpoint,
            parameters={"latent_dim": 8, "lr": 1e-4},
            metrics={"val_loss": 0.038}
        )

        # 2. Promote model to PRODUCTION
        registry.promote_model(model_id="v1.0.0", tier="PRODUCTION")
        
        # Verify physical file copies are created with tier patterns
        prod_path = registry.get_tier_checkpoint("PRODUCTION")
        self.assertIsNotNone(prod_path)
        self.assertTrue(os.path.exists(prod_path))
        self.assertTrue(prod_path.endswith("autoencoder_production.pth"))
        
        metadata = registry._load_metadata()
        self.assertEqual(metadata["tiers"]["PRODUCTION"], "v1.0.0")

        # 3. Roll out new production promotion
        registry.promote_model(model_id="v1.1.0_challenger", tier="PRODUCTION")
        prod_path_updated = registry.get_tier_checkpoint("PRODUCTION")
        self.assertTrue(prod_path_updated.endswith("autoencoder_production.pth"))
        
        metadata = registry._load_metadata()
        self.assertEqual(metadata["tiers"]["PRODUCTION"], "v1.1.0_challenger")

        # 4. Perform atomic Rollback
        registry.rollback_tier(tier="PRODUCTION")
        prod_path_rolled_back = registry.get_tier_checkpoint("PRODUCTION")
        self.assertTrue(prod_path_rolled_back.endswith("autoencoder_production.pth"))
        
        metadata = registry._load_metadata()
        self.assertEqual(metadata["tiers"]["PRODUCTION"], "v1.0.0")

    def test_structured_ai_subsystem_logger(self):
        """Assert logger generates valid schema compliant JSON files for inference/training events."""
        ai_logger = AISubsystemLogger(log_path=self.log_file)

        # 1. Log mock prediction event
        ai_logger.log_inference(
            metric_name="CPU_Load",
            anomaly_score=0.9123,
            latency_ms=12.45,
            is_anomaly=True,
            severity="WARNING",
            threshold=0.85
        )

        # 2. Log mock training phase
        ai_logger.log_training(
            model_version="v2.0.0",
            epoch=5,
            loss=0.012345,
            metrics={"val_loss": 0.015}
        )

        # Assert file created and contains valid structured records
        self.assertTrue(os.path.exists(self.log_file))
        with open(self.log_file, "r") as f:
            records = [json.loads(line) for line in f if line.strip()]

        self.assertEqual(len(records), 2)
        
        # Verify Inference record fields
        self.assertEqual(records[0]["type"], "inference")
        self.assertEqual(records[0]["metric_name"], "CPU_Load")
        self.assertEqual(records[0]["anomaly_score"], 0.9123)
        self.assertEqual(records[0]["latency_ms"], 12.45)
        self.assertTrue(records[0]["is_anomaly"])
        self.assertEqual(records[0]["severity"], "WARNING")

        # Verify Training record fields
        self.assertEqual(records[1]["type"], "training")
        self.assertEqual(records[1]["model_version"], "v2.0.0")
        self.assertEqual(records[1]["epoch"], 5)
        self.assertEqual(records[1]["loss"], 0.012345)
        self.assertEqual(records[1]["metrics"]["val_loss"], 0.015)

    def test_end_to_end_prediction_pipeline(self):
        """Verify the PredictionPipeline groups cleaning, sequence building, and scoring."""
        manager = AnomalyDetectorManager()
        pipeline = PredictionPipeline(model_manager=manager)

        # Construct raw mock dataframe with missing values & outliers
        base_time = datetime.utcnow()
        timestamps = [base_time + timedelta(seconds=i) for i in range(80)]
        
        # 10 monitoring channels/features
        features = [f"channel_{i}" for i in range(10)]
        data = {}
        data["timestamp"] = timestamps
        for feat in features:
            values = [1.0 + float(np.random.normal(0, 0.05)) for _ in range(80)]
            # Inject nan and outlier
            values[10] = np.nan
            values[45] = 15.0
            data[feat] = values

        df = pd.DataFrame(data)

        # Fit scale bounds
        pipeline.fit(df, feature_columns=features)

        # Run end-to-end prediction scoring
        results = pipeline.preprocess_and_score(
            df=df,
            feature_columns=features,
            metric_name="Integrated_Sensors"
        )

        # Verify results shape: sliding window size 80 rows, sequence length 60, expect 20 predictions
        self.assertEqual(len(results), 20)
        
        # Check transaction schema
        first_prediction = results[0]
        self.assertEqual(first_prediction["metric_name"], "Integrated_Sensors")
        self.assertGreater(first_prediction["timestamp"], 0)
        self.assertGreaterEqual(first_prediction["anomaly_score"], 0.0)
        self.assertGreater(first_prediction["latency_ms"], 0.0)
        self.assertIn(first_prediction["severity"], ["INFO", "WARNING", "CRITICAL"])
