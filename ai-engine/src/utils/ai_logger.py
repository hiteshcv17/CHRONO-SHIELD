import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, TypedDict

logger = logging.getLogger("ai_logger")


class InferenceLogEntry(TypedDict):
    type: str
    timestamp: str
    metric_name: str
    anomaly_score: float
    threshold: float
    latency_ms: float
    is_anomaly: bool
    severity: str


class TrainingLogEntry(TypedDict):
    type: str
    timestamp: str
    model_version: str
    epoch: int
    loss: float
    metrics: Dict[str, Any]


class IngestionLogEntry(TypedDict):
    type: str
    timestamp: str
    source_name: str
    status: str
    records_count: int
    latency_ms: float
    error_message: Optional[str]


class AISubsystemLogger:
    """
    Centralized JSONL logger for telemetry ML inference events, training milestones, and ingestion cycles.
    Saves structured records under `ai-engine/logs/ml_telemetry.jsonl` using append-only formatting.
    """
    def __init__(self, log_path: str = "./ai-engine/logs/ml_telemetry.jsonl"):
        self.log_path = log_path
        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)

    def _append_log(self, record: Dict[str, Any]) -> None:
        try:
            with open(self.log_path, "a") as f:
                f.write(json.dumps(record) + "\n")
        except Exception as e:
            logger.error(f"Failed to append to central AI telemetry log file: {e}")

    def log_inference(
        self,
        metric_name: str,
        anomaly_score: float,
        latency_ms: float,
        is_anomaly: bool,
        severity: str,
        threshold: float = 0.85
    ) -> InferenceLogEntry:
        """
        Record a single real-time inference prediction transaction.
        """
        record: InferenceLogEntry = {
            "type": "inference",
            "timestamp": datetime.utcnow().isoformat(),
            "metric_name": metric_name,
            "anomaly_score": round(float(anomaly_score), 4),
            "threshold": round(float(threshold), 4),
            "latency_ms": round(float(latency_ms), 3),
            "is_anomaly": bool(is_anomaly),
            "severity": severity
        }
        self._append_log(record)
        return record

    def log_training(
        self,
        model_version: str,
        epoch: int,
        loss: float,
        metrics: Dict[str, Any]
    ) -> TrainingLogEntry:
        """
        Record a training milestone epoch or completion metrics.
        """
        record: TrainingLogEntry = {
            "type": "training",
            "timestamp": datetime.utcnow().isoformat(),
            "model_version": model_version,
            "epoch": int(epoch),
            "loss": round(float(loss), 6),
            "metrics": metrics
        }
        self._append_log(record)
        return record

    def log_ingestion(
        self,
        source_name: str,
        status: str,
        records_count: int,
        latency_ms: float,
        error_message: Optional[str] = None
    ) -> IngestionLogEntry:
        """
        Record an ingestion cycle completion status.
        """
        record: IngestionLogEntry = {
            "type": "ingestion",
            "timestamp": datetime.utcnow().isoformat(),
            "source_name": source_name,
            "status": status,
            "records_count": int(records_count),
            "latency_ms": round(float(latency_ms), 3),
            "error_message": error_message
        }
        self._append_log(record)
        return record


# Shared singleton logger
ai_logger = AISubsystemLogger()
