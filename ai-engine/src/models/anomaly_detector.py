import os
import torch
import torch.nn as nn
import numpy as np
import logging
from typing import Optional, Dict, Any
from src.config import ai_settings
from src.models.base import BaseModel

logger = logging.getLogger("anomaly_detector")


class TemporalAutoencoder(nn.Module):
    """
    PyTorch Reconstruction-based Autoencoder for Time-Series Anomaly Detection.
    Attempts to compress and reconstruct normal sequence profiles.
    High reconstruction errors denote an anomalous signature.
    """

    def __init__(self, sequence_length: int, feature_dim: int, latent_dim: int = 8):
        super().__init__()
        self.sequence_length = sequence_length
        self.feature_dim = feature_dim

        # Flattened size
        self.input_dim = sequence_length * feature_dim

        # Encoder Layers
        self.encoder = nn.Sequential(
            nn.Linear(self.input_dim, 64),
            nn.ReLU(),
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Linear(32, latent_dim),
            nn.ReLU(),
        )

        # Decoder Layers
        self.decoder = nn.Sequential(
            nn.Linear(latent_dim, 32),
            nn.ReLU(),
            nn.Linear(32, 64),
            nn.ReLU(),
            nn.Linear(64, self.input_dim),
            nn.Tanh(),  # Bounds values to normalized standard scale
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Compresses and reconstructs input sequence.
        Input shape: (batch_size, sequence_length, feature_dim)
        """
        batch_size = x.size(0)
        # Flatten temporal window
        x_flat = x.view(batch_size, -1)
        # Latent space representation
        latent = self.encoder(x_flat)
        # Reconstruct
        reconstructed_flat = self.decoder(latent)
        # Unflatten back to sequence profile
        return reconstructed_flat.view(
            batch_size, self.sequence_length, self.feature_dim
        )


class AnomalyDetectorManager(BaseModel):
    """
    Orchestration layer managing weights, threshold calculations, JIT compiled models,
    and saving/loading model artifacts.
    """

    def __init__(self, latent_dim: int = 8):
        self.sequence_length = ai_settings.SEQUENCE_LENGTH
        self.feature_dim = ai_settings.FEATURE_DIMENSION
        self.model = TemporalAutoencoder(
            self.sequence_length, self.feature_dim, latent_dim
        )
        self.anomaly_threshold = ai_settings.AI_ANOMALY_THRESHOLD
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)
        logger.info(f"Model successfully mounted on execution device: {self.device}")

        # Initialize TorchScript JIT model compiler for optimized inference
        try:
            self.jit_model = torch.jit.script(self.model)
            logger.info(
                "TorchScript JIT compilation successful for TemporalAutoencoder."
            )
        except Exception as e:
            logger.warning(
                f"TorchScript compilation failed, falling back to eager PyTorch model: {e}"
            )
            self.jit_model = self.model

    def fit(self, X: Any, **kwargs: Any) -> Any:
        """
        Train the PyTorch autoencoder model on the provided data.
        X is expected to be a numpy array of shape (N, sequence_length, feature_dim) or similar tensor.
        """
        epochs = kwargs.get("epochs", ai_settings.AI_DEFAULT_EPOCHS)
        batch_size = kwargs.get("batch_size", ai_settings.AI_TRAIN_BATCH_SIZE)
        lr = kwargs.get("lr", 1e-3)

        if not isinstance(X, torch.Tensor):
            X_tensor = torch.tensor(X, dtype=torch.float32)
        else:
            X_tensor = X.float()

        dataset = torch.utils.data.TensorDataset(X_tensor)
        dataloader = torch.utils.data.DataLoader(
            dataset, batch_size=batch_size, shuffle=True
        )

        optimizer = torch.optim.Adam(self.model.parameters(), lr=lr)
        criterion = torch.nn.MSELoss()

        self.model.train()
        logger.info(
            f"Starting model training for {epochs} epochs on device: {self.device}"
        )

        for epoch in range(epochs):
            total_loss = 0.0
            for batch in dataloader:
                batch_x = batch[0].to(self.device)
                optimizer.zero_grad()
                reconstructed = self.model(batch_x)
                loss = criterion(reconstructed, batch_x)
                loss.backward()
                optimizer.step()
                total_loss += loss.item() * batch_x.size(0)

            avg_loss = total_loss / len(X_tensor)
            if (epoch + 1) % max(1, epochs // 5) == 0 or epoch == epochs - 1:
                logger.info(f"Epoch {epoch+1}/{epochs} - MSE Loss: {avg_loss:.6f}")

        # Update anomaly threshold dynamically (95th percentile of errors)
        self.model.eval()
        with torch.no_grad():
            errors = []
            for i in range(0, len(X_tensor), batch_size):
                batch_x = X_tensor[i : i + batch_size].to(self.device)
                reconstructed = self.model(batch_x)
                mse = torch.mean((batch_x - reconstructed) ** 2, dim=(1, 2))
                errors.extend(mse.cpu().numpy().tolist())
            self.anomaly_threshold = float(np.percentile(errors, 95))
            logger.info(f"Recalculated anomaly threshold: {self.anomaly_threshold:.4f}")

        # Update the JIT model compilation with newly optimized weights
        try:
            self.jit_model = torch.jit.script(self.model)
            logger.info("TorchScript JIT model successfully updated after fit.")
        except Exception as e:
            logger.warning(f"TorchScript compilation failed after fit: {e}")
            self.jit_model = self.model

        return self

    def predict(self, X: Any, **kwargs: Any) -> Any:
        """
        Runs reconstruction score inference using the JIT-compiled TorchScript model.
        Returns the reconstruction MSE scores.
        """
        return self.calculate_reconstruction_error(X)

    def save(self, path: str, **kwargs: Any) -> str:
        """
        Serialize model state checkpoint and metadata parameters.
        """
        if os.path.isdir(path):
            path = os.path.join(path, "autoencoder_latest.pth")

        dir_name = os.path.dirname(path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)

        torch.save(
            {
                "model_state_dict": self.model.state_dict(),
                "anomaly_threshold": self.anomaly_threshold,
                "sequence_length": self.sequence_length,
                "feature_dim": self.feature_dim,
            },
            path,
        )
        logger.info(f"Model checkpoint successfully saved to: {path}")
        return path

    def load(self, path: str, **kwargs: Any) -> None:
        """
        Restores model checkpoints, metadata thresholds and updates TorchScript JIT modules.
        """
        if not os.path.exists(path):
            raise FileNotFoundError(f"No serial checkpoint found matching: {path}")

        checkpoint = torch.load(path, map_location=self.device)
        self.model.load_state_dict(checkpoint["model_state_dict"])
        self.anomaly_threshold = checkpoint["anomaly_threshold"]

        # Update the compiled JIT model weights
        try:
            self.jit_model = torch.jit.script(self.model)
            logger.info(
                "TorchScript JIT model successfully updated after loading checkpoint."
            )
        except Exception as e:
            logger.warning(f"TorchScript compilation failed after load: {e}")
            self.jit_model = self.model

        logger.info(f"Model successfully restored from checkpoint: {path}")

    def save_model(self, filename: str = "autoencoder_latest.pth") -> str:
        """
        Legacy/convenience checkpoint saver. Writes to standard AI_MODEL_DIR registry path.
        """
        os.makedirs(ai_settings.AI_MODEL_DIR, exist_ok=True)
        save_path = os.path.join(ai_settings.AI_MODEL_DIR, filename)
        return self.save(save_path)

    def load_model(self, filename: str = "autoencoder_latest.pth") -> None:
        """
        Legacy/convenience checkpoint loader. Reads from standard AI_MODEL_DIR registry path.
        """
        load_path = os.path.join(ai_settings.AI_MODEL_DIR, filename)
        self.load(load_path)

    def calculate_reconstruction_error(self, x: np.ndarray) -> np.ndarray:
        """
        Calculates MSE reconstruction scores for single or batched sequences.
        """
        self.model.eval()
        if hasattr(self, "jit_model") and self.jit_model is not None:
            self.jit_model.eval()
            predictor_model = self.jit_model
        else:
            predictor_model = self.model

        with torch.no_grad():
            if isinstance(x, torch.Tensor):
                x_tensor = x.float().to(self.device)
            else:
                x_tensor = torch.tensor(x, dtype=torch.float32).to(self.device)

            # Add batch dimension if single sequence passed
            if len(x_tensor.shape) == 2:
                x_tensor = x_tensor.unsqueeze(0)

            reconstructed = predictor_model(x_tensor)
            # Compute Mean Squared Error per sequence sample
            mse = torch.mean((x_tensor - reconstructed) ** 2, dim=(1, 2))
            return mse.cpu().numpy()
