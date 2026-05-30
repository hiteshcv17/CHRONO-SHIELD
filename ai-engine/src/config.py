import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class AISettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    ENVIRONMENT: str = "development"
    PROJECT_NAME: str = "ChronoShield AI Engine"

    # AI Engine Network Settings
    AI_ENGINE_HOST: str = "0.0.0.0"
    AI_ENGINE_PORT: int = 8001
    AI_LOG_LEVEL: str = "info"

    # Directory registry for model serialization
    AI_MODEL_DIR: str = "./ai-engine/models/registry"

    # Hyperparameter defaults
    AI_TRAIN_BATCH_SIZE: int = 64
    AI_DEFAULT_EPOCHS: int = 10
    AI_ANOMALY_THRESHOLD: float = 0.85

    # Sequence / Window settings for Temporal Analytics
    SEQUENCE_LENGTH: int = 60  # Length of sliding sequence history analyzed (e.g. 60 steps)
    FEATURE_DIMENSION: int = 10  # Number of metric channels monitored

    # Redis Connection details (for sequence streams and pub/sub logs)
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: Optional[str] = "secure_redis_pass_112"
    REDIS_DB: int = 0

    # PostgreSQL Connection details (for time-series historical data persistence)
    DATABASE_URL: Optional[str] = "postgresql+asyncpg://postgres:secure_postgres_pass_998@localhost:5432/chronoshield_db"

    # Global Logs Folder
    LOGS_DIR: str = "./logs"

    # Enterprise AI Performance Tuning
    AI_MAX_INFERENCE_WORKERS: int = 4
    AI_METRICS_ENABLED: bool = True



ai_settings = AISettings()
