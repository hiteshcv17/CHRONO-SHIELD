import os
import json
import shutil
import tempfile
import unittest
import numpy as np
from fastapi.testclient import TestClient
from src.main import app
from src.ml.registry import ModelRegistryManager


class TestAIMicroserviceAPI(unittest.TestCase):
    """
    Integration verification suite for the ChronoShield AI Engine REST Microservice API.
    """

    def setUp(self):
        # Create a temporary workspace for registries
        self.test_dir = tempfile.mkdtemp()
        self.registry_dir = os.path.join(self.test_dir, "registry")
        
        # Override the app state registry to isolate test side-effects
        app.state.registry = ModelRegistryManager(registry_dir=self.registry_dir)
        self.client = TestClient(app)

    def tearDown(self):
        # Cleanup temporary files
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_health_check_endpoint(self):
        """Assert health endpoint returns dynamic app status and active settings."""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "healthy")
        self.assertIn("environment", data)
        self.assertIn("active_production_model", data)

    def test_predict_anomaly_endpoint(self):
        """Assert predict endpoint executes optimized autoencoder inference."""
        # Generate normal sequence mock shape (60, 10)
        mock_seq = np.random.normal(0.0, 0.2, (60, 10)).tolist()

        payload = {
            "sequence": mock_seq,
            "metric_name": "CPU_Usage"
        }

        response = self.client.post("/api/v1/predict", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["metric_name"], "CPU_Usage")
        self.assertIn("anomaly_score", data)
        self.assertIn("threshold", data)
        self.assertIn("is_anomaly", data)
        self.assertIn("severity", data)
        self.assertIn("latency_ms", data)

    def test_end_to_end_training_and_registry_lifecycle(self):
        """Assert training triggers, model catalog registers, promotion, and rollbacks via API endpoints."""
        # 1. Register a dummy model checkpoint first
        dummy_checkpoint = os.path.join(self.test_dir, "dummy.pth")
        import torch
        torch.save({"state": [1, 2, 3]}, dummy_checkpoint)
        app.state.registry.register_model(
            model_id="v1.0.0_baseline",
            checkpoint_path=dummy_checkpoint,
            parameters={"latent_dim": 8},
            metrics={"val_loss": 0.05}
        )

        # 2. Trigger model training via API (3D data shape (5, 60, 10))
        mock_data = np.random.normal(0.0, 0.1, (5, 60, 10)).tolist()
        train_payload = {
            "data": mock_data,
            "model_id": "v1.1.0_trained",
            "epochs": 2,
            "batch_size": 2,
            "lr": 1e-3
        }

        response = self.client.post("/api/v1/predict/train", json=train_payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["model_id"], "v1.1.0_trained")
        self.assertIn("registry_entry", data)

        # 3. Retrieve model catalog from endpoint
        catalog_response = self.client.get("/api/v1/registry/models")
        self.assertEqual(catalog_response.status_code, 200)
        catalog = catalog_response.json()
        self.assertIn("v1.0.0_baseline", catalog["models"])
        self.assertIn("v1.1.0_trained", catalog["models"])

        # 4. Promote baseline model to PRODUCTION
        promote_payload = {
            "model_id": "v1.0.0_baseline",
            "tier": "PRODUCTION"
        }
        promote_response = self.client.post("/api/v1/registry/promote", json=promote_payload)
        self.assertEqual(promote_response.status_code, 200)
        self.assertEqual(promote_response.json()["status"], "success")

        catalog_updated_1 = self.client.get("/api/v1/registry/models").json()
        self.assertEqual(catalog_updated_1["tiers"]["PRODUCTION"], "v1.0.0_baseline")

        # 5. Promote trained model to PRODUCTION
        promote_payload_2 = {
            "model_id": "v1.1.0_trained",
            "tier": "PRODUCTION"
        }
        promote_response_2 = self.client.post("/api/v1/registry/promote", json=promote_payload_2)
        self.assertEqual(promote_response_2.status_code, 200)

        catalog_updated_2 = self.client.get("/api/v1/registry/models").json()
        self.assertEqual(catalog_updated_2["tiers"]["PRODUCTION"], "v1.1.0_trained")

        # 6. Perform rollback to previous baseline model via API
        rollback_payload = {
            "tier": "PRODUCTION"
        }
        rollback_response = self.client.post("/api/v1/registry/rollback", json=rollback_payload)
        self.assertEqual(rollback_response.status_code, 200)
        self.assertEqual(rollback_response.json()["status"], "success")

        catalog_rolled_back = self.client.get("/api/v1/registry/models").json()
        self.assertEqual(catalog_rolled_back["tiers"]["PRODUCTION"], "v1.0.0_baseline")
