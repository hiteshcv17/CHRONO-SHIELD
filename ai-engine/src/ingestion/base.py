"""
ai-engine/src/ingestion/base.py

Abstract base layer for all ChronoShield AI data sources.
Every concrete source MUST inherit from BaseDataSource and
implement the abstract methods defined here.
"""

from __future__ import annotations

import abc
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger("ingestion.base")


# ==============================================================================
# Shared Enumerations
# ==============================================================================


class SourceCategory(str, Enum):
    WEATHER = "weather"
    TRAFFIC = "traffic"
    ENERGY = "energy"
    SOCIAL_MEDIA = "social_media"
    INFRASTRUCTURE = "infrastructure"
    CUSTOM = "custom"


class IngestionStatus(str, Enum):
    SUCCESS = "success"
    PARTIAL = "partial"  # Some records failed validation
    SKIPPED = "skipped"  # Source disabled or rate-limited
    FAILED = "failed"  # Unrecoverable error


class HealthState(str, Enum):
    REACHABLE = "reachable"
    UNREACHABLE = "unreachable"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


# ==============================================================================
# Shared Dataclasses (typed contracts across the pipeline)
# ==============================================================================


@dataclass
class IngestionResult:
    """
    Unified result returned by every data source's fetch() call.
    Downstream pipeline components consume this contract exclusively.
    """

    source_name: str
    status: IngestionStatus
    fetched_at: datetime = field(default_factory=datetime.utcnow)
    record_count: int = 0
    records_count: int = 0
    records: List[Dict[str, Any]] = field(default_factory=list)
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.records_count and self.record_count:
            self.records_count = self.record_count
        elif not self.record_count and self.records_count:
            self.record_count = self.records_count

    def is_successful(self) -> bool:
        return self.status in (IngestionStatus.SUCCESS, IngestionStatus.PARTIAL)

    def summary(self) -> str:
        return (
            f"[{self.source_name}] status={self.status.value} "
            f"records={self.record_count} at={self.fetched_at.isoformat()}"
        )


@dataclass
class SourceMetadata:
    """
    Static descriptors returned by get_metadata().
    Used by the registry and dashboard status views.
    """

    name: str
    version: str
    category: SourceCategory
    description: str
    interval_seconds: int  # Default polling cadence
    supported_fields: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    source_type: str = ""

    def __post_init__(self):
        if not self.source_type:
            self.source_type = self.category.value


@dataclass
class SourceHealthStatus:
    """
    Runtime health snapshot returned by health_check().
    """

    source_name: str
    state: HealthState
    checked_at: datetime = field(default_factory=datetime.utcnow)
    latency_ms: Optional[float] = None
    detail: Optional[str] = None


# ==============================================================================
# Abstract Base Class
# ==============================================================================


class BaseDataSource(abc.ABC):
    """
    Contract that all data source implementations must satisfy.

    Lifecycle:
        1. __init__(config: SourceConfig)          — store config
        2. validate()                              — assert config is complete
        3. health_check()    (optional pre-fetch)  — ping endpoint
        4. fetch()                                 — pull records → IngestionResult
    """

    def __init__(self, config: "SourceConfig") -> None:  # noqa: F821
        self.config = config
        self._logger = logging.getLogger(f"ingestion.{self.get_metadata().name}")

    # ------------------------------------------------------------------
    # Abstract interface — MUST be implemented by every subclass
    # ------------------------------------------------------------------

    @abc.abstractmethod
    async def fetch(self) -> IngestionResult:
        """
        Pull raw records from the upstream data source.
        Must return a fully populated IngestionResult — never raise.
        Handle internal exceptions and encode them in result.error_message.
        """
        ...

    @abc.abstractmethod
    def get_metadata(self) -> SourceMetadata:
        """Return static descriptor for this source."""
        ...

    # ------------------------------------------------------------------
    # Concrete helpers — may be overridden for custom behaviour
    # ------------------------------------------------------------------

    def validate(self) -> bool:
        """
        Verify that the SourceConfig contains all required fields.
        Override to add source-specific validation logic.
        """
        required = ["endpoint", "interval_seconds"]
        for field_name in required:
            if not getattr(self.config, field_name, None):
                self._logger.warning(
                    f"Validation failed: missing required config field '{field_name}'"
                )
                return False
        return True

    async def health_check(self) -> SourceHealthStatus:
        """
        Lightweight reachability probe.
        Default implementation returns UNKNOWN — sources should override
        with a real HEAD/ping request once API integration is active.
        """
        return SourceHealthStatus(
            source_name=self.get_metadata().name,
            state=HealthState.UNKNOWN,
            detail="Health check not yet implemented for this source.",
        )

    def __repr__(self) -> str:
        meta = self.get_metadata()
        return (
            f"<{self.__class__.__name__} "
            f"name={meta.name!r} category={meta.category.value!r} "
            f"enabled={self.config.enabled}>"
        )
