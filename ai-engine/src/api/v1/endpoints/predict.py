import time
import os
import tempfile
import numpy as np
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from src.inference.predictor import RealTimePredictor
from src.models.anomaly_detector import AnomalyDetectorManager
from src.ml.registry import ModelRegistryManager
from src.utils.ai_logger import ai_logger
from src.utils.prometheus import (
    ANOMALIES_DETECTED,
    INFERENCE_TIME,
    MODEL_TRAINING_TIME,
)

router = APIRouter(prefix="/predict", tags=["Predictions"])


class PredictionRequest(BaseModel):
    sequence: List[List[float]] = Field(
        ..., description="2D sequence list of shape (sequence_length, feature_dim)"
    )
    metric_name: Optional[str] = Field(
        "System_Metrics", description="The label name of the metric sequence group."
    )


class PredictionResponse(BaseModel):
    metric_name: str = Field(
        ..., description="The label name of the metric sequence group."
    )
    anomaly_score: float = Field(
        ..., description="Calculated reconstruction error score."
    )
    threshold: float = Field(
        ..., description="The threshold used to determine if it is an anomaly."
    )
    is_anomaly: bool = Field(
        ..., description="True if the sequence was flagged as anomalous."
    )
    severity: str = Field(
        ..., description="Severity classification (CRITICAL, WARNING, NOMINAL, INFO)."
    )
    latency_ms: float = Field(
        ..., description="Prediction inference execution latency in milliseconds."
    )
    timestamp: float = Field(..., description="POSIX timestamp of inference execution.")


class TrainingRequest(BaseModel):
    data: List[List[List[float]]] = Field(
        ...,
        description="3D dataset array of shape (num_samples, sequence_length, feature_dim)",
    )
    model_id: str = Field(
        ..., description="Unique model version identifier to register after training."
    )
    epochs: Optional[int] = Field(None, description="Number of training epochs.")
    batch_size: Optional[int] = Field(
        None, description="Batch size for gradient descent."
    )
    lr: Optional[float] = Field(1e-3, description="Optimizer learning rate.")


class TrainingResponse(BaseModel):
    status: str = Field(..., description="The overall training execution status")
    model_id: str = Field(..., description="The registered model unique identifier")
    registry_entry: Dict[str, Any] = Field(
        ..., description="Metadata record entry saved in the model registry"
    )


def _save_temp_checkpoint(manager: AnomalyDetectorManager, model_id: str) -> str:
    """Helper to save the current model checkpoint to a temporary path."""
    temp_dir = tempfile.gettempdir()
    temp_checkpoint = os.path.join(temp_dir, f"{model_id}_temp.pth")
    manager.save(temp_checkpoint)
    return temp_checkpoint


def _register_checkpoint(
    request: Request,
    model_id: str,
    checkpoint_path: str,
    manager: AnomalyDetectorManager,
    epochs: Optional[int],
    lr: Optional[float],
    duration_sec: float,
) -> Dict[str, Any]:
    """Helper to register the trained checkpoint with the registry manager."""
    registry = getattr(request.app.state, "registry", None)
    if not registry:
        registry = ModelRegistryManager()

    entry = registry.register_model(
        model_id=model_id,
        checkpoint_path=checkpoint_path,
        parameters={
            "epochs": epochs or manager.sequence_length,
            "batch_size": 64,
            "latent_dim": 8,
            "lr": lr,
        },
        metrics={
            "fit_duration_seconds": round(duration_sec, 2),
            "final_reconstruction_threshold": round(manager.anomaly_threshold, 6),
        },
    )
    return entry


@router.post(
    "", response_model=PredictionResponse, summary="Perform real-time anomaly detection"
)
def predict_anomaly(payload: PredictionRequest) -> PredictionResponse:
    """
    Ingest a temporal metric sequence, apply JIT-optimized inference autoencoders,
    and output reconstruction anomaly metrics and severity classification.
    """
    try:
        sequence_np = np.array(payload.sequence, dtype=np.float32)
        # Instantiate predictor dynamically to ensure the latest promoted model weights are loaded
        predictor = RealTimePredictor()

        start_time = time.time()
        result = predictor.analyze_sequence(
            sequence_np, metric_name=payload.metric_name
        )
        inference_duration = time.time() - start_time

        # Record Prometheus inference latency
        INFERENCE_TIME.labels(model_type="temporal_autoencoder").observe(
            inference_duration
        )

        # Record anomaly detection count if this result is flagged as an anomaly
        is_anomaly = (
            result.get("is_anomaly", False) if isinstance(result, dict) else False
        )
        severity = (
            result.get("severity", "UNKNOWN") if isinstance(result, dict) else "UNKNOWN"
        )
        if is_anomaly:
            ANOMALIES_DETECTED.labels(
                metric_name=payload.metric_name or "unknown", severity=severity
            ).inc()

        return PredictionResponse(**result)
    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"Inference execution failed: {str(e)}"
        )


@router.post(
    "/train",
    response_model=TrainingResponse,
    summary="Train and register a new autoencoder model",
)
def train_model(payload: TrainingRequest, request: Request) -> TrainingResponse:
    """
    Fits a new PyTorch TemporalAutoencoder on 3D training sequences,
    saves the optimized weights, and registers the checkpoint under the model registry.
    """
    try:
        data_np = np.array(payload.data, dtype=np.float32)
        manager = AnomalyDetectorManager()

        # Parse hyperparameters
        fit_kwargs = {}
        if payload.epochs is not None:
            fit_kwargs["epochs"] = payload.epochs
        if payload.batch_size is not None:
            fit_kwargs["batch_size"] = payload.batch_size
        if payload.lr is not None:
            fit_kwargs["lr"] = payload.lr

        # Fit model on custom metrics, record training duration
        start_time = time.time()
        manager.fit(data_np, **fit_kwargs)
        duration_sec = time.time() - start_time

        # Record Prometheus training duration
        MODEL_TRAINING_TIME.labels(model_type="temporal_autoencoder").observe(
            duration_sec
        )

        # Save to a temporary file using the private helper
        temp_checkpoint = _save_temp_checkpoint(manager, payload.model_id)

        # Register checkpoint using private helper
        entry = _register_checkpoint(
            request=request,
            model_id=payload.model_id,
            checkpoint_path=temp_checkpoint,
            manager=manager,
            epochs=payload.epochs,
            lr=payload.lr,
            duration_sec=duration_sec,
        )

        # Cleanup temp file
        if os.path.exists(temp_checkpoint):
            os.remove(temp_checkpoint)

        # Structured logger training logging
        ai_logger.log_training(
            model_version=payload.model_id,
            epoch=payload.epochs or 10,
            loss=0.0,
            metrics=entry["metrics"],
        )

        return TrainingResponse(
            status="success", model_id=payload.model_id, registry_entry=entry
        )
    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"Training orchestration failed: {str(e)}"
        )
