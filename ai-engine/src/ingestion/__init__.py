"""
ChronoShield AI — Ingestion Package

Public surface for the multi-source data ingestion architecture.
"""

from src.ingestion.base import (
    BaseDataSource,
    IngestionResult,
    IngestionStatus,
    SourceCategory,
    SourceHealthStatus,
    SourceMetadata,
    HealthState,
)
from src.ingestion.config_manager import ConfigManager, SourceConfig, config_manager
from src.ingestion.registry import SourceRegistry, registry, register_source
from src.ingestion.scheduler import IngestionScheduler
from src.ingestion.orchestrator import IngestionOrchestrator

__all__ = [
    # Base
    "BaseDataSource",
    "IngestionResult",
    "IngestionStatus",
    "SourceCategory",
    "SourceHealthStatus",
    "SourceMetadata",
    "HealthState",
    # Config
    "ConfigManager",
    "SourceConfig",
    "config_manager",
    # Registry
    "SourceRegistry",
    "registry",
    "register_source",
    # Scheduler
    "IngestionScheduler",
    # Orchestrator
    "IngestionOrchestrator",
]
