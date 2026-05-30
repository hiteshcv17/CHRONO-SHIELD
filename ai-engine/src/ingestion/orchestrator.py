"""
ai-engine/src/ingestion/orchestrator.py

IngestionOrchestrator — top-level coordinator for the ChronoShield AI
multi-source data ingestion pipeline.

Responsibilities:
    1. Load SourceConfig for all declared sources via ConfigManager
    2. Hydrate the SourceRegistry with instantiated source objects
    3. Start the IngestionScheduler (registers APScheduler cron jobs)
    4. Expose status() for runtime observability

Run as a standalone smoke test:
    cd ai-engine
    python -m src.ingestion.orchestrator
"""

from __future__ import annotations

import asyncio
import logging
import signal
import sys
from datetime import datetime
from typing import Dict, List, Optional

# Trigger self-registration of all source stubs via decorator
import src.ingestion.sources.weather  # noqa: F401
import src.ingestion.sources.traffic  # noqa: F401
import src.ingestion.sources.energy  # noqa: F401
import src.ingestion.sources.social  # noqa: F401

from src.ingestion.base import BaseDataSource, HealthState, SourceHealthStatus
from src.ingestion.config_manager import ConfigManager, SourceConfig
from src.ingestion.registry import registry, SourceRegistry
from src.ingestion.scheduler import IngestionScheduler

logger = logging.getLogger("ingestion.orchestrator")


# ==============================================================================
# Runtime Source Record
# ==============================================================================


class SourceRecord:
    """Holds runtime state of a single ingested source."""

    def __init__(
        self,
        config: SourceConfig,
        instance: Optional[BaseDataSource],
    ) -> None:
        self.config = config
        self.instance = instance
        self.registered_at: datetime = datetime.utcnow()
        self.last_health: Optional[SourceHealthStatus] = None

    @property
    def is_valid(self) -> bool:
        return self.instance is not None and self.instance.validate()


# ==============================================================================
# Orchestrator
# ==============================================================================


class IngestionOrchestrator:
    """
    Central coordinator for the multi-source ingestion pipeline.

    Wires together:
        ConfigManager → SourceRegistry → IngestionScheduler
    """

    def __init__(
        self,
        config_manager: Optional[ConfigManager] = None,
        source_registry: Optional[SourceRegistry] = None,
    ) -> None:
        self._config_manager = config_manager or ConfigManager()
        self._registry = source_registry or registry
        self._scheduler = IngestionScheduler()
        self._records: Dict[str, SourceRecord] = {}
        self._started_at: Optional[datetime] = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def initialize(self) -> None:
        """
        Load configs, instantiate all registered sources, and
        prepare scheduler jobs. Does NOT start polling.
        """
        logger.info("Initializing IngestionOrchestrator...")
        self._config_manager.load()

        all_configs = self._config_manager.list_all()

        if not all_configs:
            logger.warning(
                "No source configurations found. "
                "Check ai-engine/configs/sources.yaml."
            )

        sources_for_scheduler: List[BaseDataSource] = []

        for cfg in all_configs:
            instance = self._registry.instantiate(cfg.name, cfg)
            record = SourceRecord(config=cfg, instance=instance)
            self._records[cfg.name] = record

            if instance and cfg.enabled and record.is_valid:
                sources_for_scheduler.append(instance)
            else:
                reason = (
                    "not registered in registry"
                    if instance is None
                    else "disabled" if not cfg.enabled else "failed validation"
                )
                logger.info(
                    f"Skipping scheduler registration for '{cfg.name}': {reason}"
                )

        self._scheduler.add_sources(sources_for_scheduler)
        logger.info(
            f"Orchestrator initialized: "
            f"{len(self._records)} source(s) hydrated, "
            f"{self._scheduler.source_count} scheduled."
        )

    async def start(self) -> None:
        """Start the scheduler — sources begin polling on their intervals."""
        await self.initialize()
        await self._scheduler.start()
        self._started_at = datetime.utcnow()
        logger.info("IngestionOrchestrator started.")

    async def stop(self) -> None:
        """Gracefully shut down the scheduler."""
        await self._scheduler.stop()
        logger.info("IngestionOrchestrator stopped.")

    # ------------------------------------------------------------------
    # Observability
    # ------------------------------------------------------------------

    def status(self) -> dict:
        """Return serializable runtime status of all sources."""
        return {
            "started_at": self._started_at.isoformat() if self._started_at else None,
            "scheduler_running": self._scheduler.is_running,
            "total_sources": len(self._records),
            "enabled_sources": sum(
                1 for r in self._records.values() if r.config.enabled
            ),
            "scheduler_jobs": self._scheduler.get_jobs(),
            "sources": [
                {
                    "name": cfg_name,
                    "enabled": record.config.enabled,
                    "registered": record.instance is not None,
                    "valid": record.is_valid,
                    "interval_seconds": record.config.interval_seconds,
                    "endpoint": record.config.endpoint,
                    "api_key_set": bool(record.config.api_key),
                    "registered_at": record.registered_at.isoformat(),
                }
                for cfg_name, record in self._records.items()
            ],
        }

    def print_status_table(self) -> None:
        """Print a rich terminal status table for the smoke test."""
        status = self.status()
        width = 82

        print("\n" + "═" * width)
        print("  🛡  ChronoShield AI — Ingestion Orchestrator Status")
        print("═" * width)
        print(f"  Started at    : {status['started_at'] or 'Not started'}")
        print(
            f"  Scheduler     : {'▶ RUNNING' if status['scheduler_running'] else '◼ STOPPED'}"
        )
        print(f"  Total sources : {status['total_sources']}")
        print(f"  Enabled       : {status['enabled_sources']}")
        print("─" * width)
        print(
            f"  {'SOURCE':<12} {'ENABLED':<9} {'REGISTERED':<12} {'VALID':<8} {'INTERVAL':<12} {'KEY SET'}"
        )
        print("─" * width)

        for src in status["sources"]:
            enabled = "✓ Yes" if src["enabled"] else "✗ No"
            registered = "✓ Yes" if src["registered"] else "✗ No"
            valid = "✓ Yes" if src["valid"] else "✗ No"
            key_set = "✓ Yes" if src["api_key_set"] else "✗ No (env)"
            interval = f"{src['interval_seconds']}s"

            print(
                f"  {src['name']:<12} {enabled:<9} {registered:<12} "
                f"{valid:<8} {interval:<12} {key_set}"
            )

        print("─" * width)
        print(f"  Scheduled Jobs ({len(status['scheduler_jobs'])}):")
        for job in status["scheduler_jobs"]:
            next_run = job.get("next_run") or "N/A"
            print(f"    [{job['status'].upper():<10}] {job['id']} → next: {next_run}")

        print("═" * width + "\n")


# ==============================================================================
# Standalone smoke-test entry point
# ==============================================================================


async def _main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )

    orchestrator = IngestionOrchestrator()
    await orchestrator.start()
    orchestrator.print_status_table()

    # In a real deployment, keep running until signal:
    #   await asyncio.Event().wait()
    # For smoke test, stop immediately after status print.
    await orchestrator.stop()
    logger.info("Smoke test complete.")


if __name__ == "__main__":
    asyncio.run(_main())
