"""
ai-engine/src/ingestion/scheduler.py

IngestionScheduler — APScheduler-based async job scheduler.

Each enabled data source is registered as an AsyncIOScheduler cron job
using its configured interval_seconds. In Phase 5 (stub phase), jobs
trigger but call placeholder fetch() methods that return IngestionStatus.SKIPPED.

When real API integration is added in future phases, no scheduler changes
are needed — only the source's fetch() implementation changes.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional

try:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.interval import IntervalTrigger
    from apscheduler.job import Job
    _APSCHEDULER_AVAILABLE = True
except ImportError:
    _APSCHEDULER_AVAILABLE = False

from src.ingestion.base import BaseDataSource, IngestionResult, IngestionStatus
from src.ingestion.persistence import persist_ingestion_result

logger = logging.getLogger("ingestion.scheduler")


# ==============================================================================
# Job execution wrapper
# ==============================================================================

async def _run_source_job(source: BaseDataSource) -> None:
    """
    Async wrapper executed by APScheduler for each source poll cycle.
    Logs result summary; downstream consumers (pipeline, DB writer) will
    hook into this function in future phases.
    """
    meta = source.get_metadata()
    logger.info(f"[Scheduler] Job fired → source='{meta.name}'")

    try:
        result: IngestionResult = await source.fetch()
        logger.info(f"[Scheduler] {result.summary()}")

        # Persist metrics directly to Redis Cache and time-series streams
        await persist_ingestion_result(result)

        # Record ingestion counts in Prometheus
        try:
            from src.utils.prometheus import INGESTION_COUNT
            records_count = getattr(result, "records_count", 1)
            source_type = getattr(meta, "source_type", "unknown")
            INGESTION_COUNT.labels(source_type=source_type).inc(records_count)
        except Exception as prom_exc:
            logger.warning(f"[Scheduler] Failed to record ingestion Prometheus metric: {prom_exc}")

    except Exception as exc:
        logger.error(
            f"[Scheduler] Unhandled exception in source='{meta.name}': {exc}",
            exc_info=True,
        )


# ==============================================================================
# IngestionScheduler
# ==============================================================================

class IngestionScheduler:
    """
    Schedules and manages periodic execution of all registered data sources.

    Usage:
        scheduler = IngestionScheduler()
        scheduler.add_sources(source_instances)
        await scheduler.start()
        ...
        await scheduler.stop()
    """

    def __init__(self) -> None:
        if not _APSCHEDULER_AVAILABLE:
            logger.warning(
                "APScheduler not installed. Scheduler will run in stub mode. "
                "Install via: pip install apscheduler"
            )
        self._scheduler: Optional["AsyncIOScheduler"] = (
            AsyncIOScheduler(timezone="UTC") if _APSCHEDULER_AVAILABLE else None
        )
        self._sources: Dict[str, BaseDataSource] = {}
        self._running: bool = False

    # ------------------------------------------------------------------
    # Source management
    # ------------------------------------------------------------------

    def add_source(self, source: BaseDataSource) -> None:
        """
        Register a source and create its scheduled job.
        Must be called before start().
        """
        meta = source.get_metadata()
        self._sources[meta.name] = source

        if self._scheduler is None:
            logger.warning(
                f"[Scheduler] APScheduler unavailable — '{meta.name}' "
                "registered but job not scheduled."
            )
            return

        interval = source.config.interval_seconds
        job_id = f"job_{meta.name}"

        self._scheduler.add_job(
            func=_run_source_job,
            trigger=IntervalTrigger(seconds=interval),
            args=[source],
            id=job_id,
            name=f"Ingest: {meta.name}",
            replace_existing=True,
            max_instances=1,          # Prevent overlapping runs
            coalesce=True,            # Merge missed fires into one
            misfire_grace_time=30,    # Allow 30s late execution
        )
        logger.info(
            f"[Scheduler] Registered job '{job_id}' → "
            f"source='{meta.name}' interval={interval}s"
        )

    def add_sources(self, sources: List[BaseDataSource]) -> None:
        """Batch-register multiple sources."""
        for source in sources:
            self.add_source(source)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        if self._scheduler is None:
            logger.warning("[Scheduler] Running in stub mode — no jobs will fire.")
            self._running = True
            return

        if self._running:
            logger.warning("[Scheduler] Already running.")
            return

        self._scheduler.start()
        self._running = True
        logger.info(
            f"[Scheduler] Started. "
            f"Active jobs: {len(self._scheduler.get_jobs())}"
        )

    async def stop(self) -> None:
        if self._scheduler and self._running:
            self._scheduler.shutdown(wait=False)
        self._running = False
        logger.info("[Scheduler] Stopped.")

    # ------------------------------------------------------------------
    # Job control
    # ------------------------------------------------------------------

    def pause_source(self, source_name: str) -> bool:
        """Pause the scheduled job for a specific source."""
        if self._scheduler is None:
            return False
        job = self._scheduler.get_job(f"job_{source_name}")
        if job:
            job.pause()
            logger.info(f"[Scheduler] Paused job for source='{source_name}'")
            return True
        logger.warning(f"[Scheduler] No job found for source='{source_name}'")
        return False

    def resume_source(self, source_name: str) -> bool:
        """Resume a previously paused source job."""
        if self._scheduler is None:
            return False
        job = self._scheduler.get_job(f"job_{source_name}")
        if job:
            job.resume()
            logger.info(f"[Scheduler] Resumed job for source='{source_name}'")
            return True
        return False

    def get_jobs(self) -> List[dict]:
        """Return status of all scheduled jobs as a serializable list."""
        if self._scheduler is None:
            return [
                {
                    "id": f"job_{name}",
                    "source": name,
                    "status": "stub_mode",
                    "next_run": None,
                }
                for name in self._sources
            ]
        jobs = []
        for job in self._scheduler.get_jobs():
            next_run_time = getattr(job, "next_run_time", None)
            jobs.append({
                "id": job.id,
                "source": job.id.replace("job_", ""),
                "name": job.name,
                "next_run": next_run_time.isoformat() if next_run_time else None,
                "status": "active" if next_run_time else "paused",
            })
        return jobs

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def source_count(self) -> int:
        return len(self._sources)
