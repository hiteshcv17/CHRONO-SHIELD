import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import PrioritizedAlertRecord
from app.schemas.anomaly import AnomalyCreate
from app.core.exceptions import AppHTTPException, ErrorCode
from app.utils.constants import SeverityWeight, AlertConstants
from app.configs.settings import settings
from fastapi import status

logger = logging.getLogger("alert_service")

# Standard in-memory fallback registry for prioritized alerts in dev/testing
_MOCK_ALERTS_REGISTRY: List[PrioritizedAlertRecord] = [
    PrioritizedAlertRecord(
        id="alert-001",
        anomaly_id="anom-098",
        metric_name="CPU_Usage",
        original_severity="CRITICAL",
        current_severity="CRITICAL",
        priority_score=85.0,
        status="ACTIVE",
        occurrence_count=3,
        timestamp=datetime.utcnow() - timedelta(seconds=45), # breached >30s for demo
        last_occurrence=datetime.utcnow() - timedelta(seconds=10),
        cooldown_until=None,
        escalation_level=0,
        description="CPU load spiked anomalously beyond standard weekly deviation threshold."
    ),
    PrioritizedAlertRecord(
        id="alert-002",
        anomaly_id="anom-099",
        metric_name="Database_Latency",
        original_severity="WARNING",
        current_severity="WARNING",
        priority_score=42.5,
        status="ACKNOWLEDGED",
        occurrence_count=1,
        timestamp=datetime.utcnow() - timedelta(minutes=5),
        last_occurrence=datetime.utcnow() - timedelta(minutes=5),
        cooldown_until=datetime.utcnow() + timedelta(minutes=1),
        escalation_level=0,
        description="Connection pool saturation detected triggering high-percentile transaction delays."
    )
]


class AlertRepository:
    """Repository class for executing SQL queries on prioritized alerts."""

    @staticmethod
    async def get_active_cooldown_alert(db: Optional[AsyncSession], metric: str, now: datetime) -> Optional[PrioritizedAlertRecord]:
        """Fetch alert for the metric that has active cooldown."""
        if db is None:
            cooldown_matches = [
                a for a in _MOCK_ALERTS_REGISTRY
                if a.metric_name == metric and a.cooldown_until and a.cooldown_until > now
            ]
            return cooldown_matches[0] if cooldown_matches else None

        stmt = select(PrioritizedAlertRecord).where(
            PrioritizedAlertRecord.metric_name == metric,
            PrioritizedAlertRecord.cooldown_until > now
        ).order_by(PrioritizedAlertRecord.cooldown_until.desc())
        try:
            res = await db.execute(stmt)
            record = res.scalars().first()
            if record is not None:
                return record
        except Exception as e:
            if settings.ENVIRONMENT != "production":
                logger.warning(f"DB cooldown query failed in dev mode, falling back to mock: {e}")
                cooldown_matches = [
                    a for a in _MOCK_ALERTS_REGISTRY
                    if a.metric_name == metric and a.cooldown_until and a.cooldown_until > now
                ]
                return cooldown_matches[0] if cooldown_matches else None
            raise e

        if settings.ENVIRONMENT != "production":
            cooldown_matches = [
                a for a in _MOCK_ALERTS_REGISTRY
                if a.metric_name == metric and a.cooldown_until and a.cooldown_until > now
            ]
            if cooldown_matches:
                return cooldown_matches[0]

        return None

    @staticmethod
    async def get_duplicate_alert(db: Optional[AsyncSession], metric: str, five_min_ago: datetime) -> Optional[PrioritizedAlertRecord]:
        """Fetch duplicate active/escalated alert within the last 5 minutes."""
        if db is None:
            dup_matches = [
                a for a in _MOCK_ALERTS_REGISTRY
                if a.metric_name == metric and a.status in ["ACTIVE", "ESCALATED"] and a.last_occurrence >= five_min_ago
            ]
            return dup_matches[0] if dup_matches else None

        stmt = select(PrioritizedAlertRecord).where(
            PrioritizedAlertRecord.metric_name == metric,
            PrioritizedAlertRecord.status.in_(["ACTIVE", "ESCALATED"]),
            PrioritizedAlertRecord.last_occurrence >= five_min_ago
        ).order_by(PrioritizedAlertRecord.timestamp.desc())
        try:
            res = await db.execute(stmt)
            record = res.scalars().first()
            if record is not None:
                return record
        except Exception as e:
            if settings.ENVIRONMENT != "production":
                logger.warning(f"DB duplicate check failed in dev, falling back to mock: {e}")
                dup_matches = [
                    a for a in _MOCK_ALERTS_REGISTRY
                    if a.metric_name == metric and a.status in ["ACTIVE", "ESCALATED"] and a.last_occurrence >= five_min_ago
                ]
                return dup_matches[0] if dup_matches else None
            raise e

        if settings.ENVIRONMENT != "production":
            dup_matches = [
                a for a in _MOCK_ALERTS_REGISTRY
                if a.metric_name == metric and a.status in ["ACTIVE", "ESCALATED"] and a.last_occurrence >= five_min_ago
            ]
            if dup_matches:
                return dup_matches[0]

        return None

    @staticmethod
    async def get_alert_by_id(db: Optional[AsyncSession], alert_id: str) -> Optional[PrioritizedAlertRecord]:
        """Fetch alert by unique ID."""
        if db is None:
            matches = [x for x in _MOCK_ALERTS_REGISTRY if x.id == alert_id]
            return matches[0] if matches else None

        stmt = select(PrioritizedAlertRecord).where(PrioritizedAlertRecord.id == alert_id)
        try:
            res = await db.execute(stmt)
            record = res.scalar_one_or_none()
            if record is not None:
                return record
        except Exception as e:
            if settings.ENVIRONMENT != "production":
                logger.warning(f"DB fetch by id failed in dev, falling back to mock: {e}")
                matches = [x for x in _MOCK_ALERTS_REGISTRY if x.id == alert_id]
                return matches[0] if matches else None
            raise e

        if settings.ENVIRONMENT != "production":
            matches = [x for x in _MOCK_ALERTS_REGISTRY if x.id == alert_id]
            if matches:
                return matches[0]

        return None

    @staticmethod
    async def get_breached_alerts(db: Optional[AsyncSession], sla_cutoff: datetime) -> List[PrioritizedAlertRecord]:
        """Fetch active/escalated alerts breached since SLA cutoff that aren't escalated yet."""
        if db is None:
            return [
                a for a in _MOCK_ALERTS_REGISTRY
                if a.status in ["ACTIVE", "ESCALATED"] and a.timestamp <= sla_cutoff and a.escalation_level == 0
            ]

        stmt = select(PrioritizedAlertRecord).where(
            PrioritizedAlertRecord.status.in_(["ACTIVE", "ESCALATED"]),
            PrioritizedAlertRecord.timestamp <= sla_cutoff,
            PrioritizedAlertRecord.escalation_level == 0
        )
        try:
            res = await db.execute(stmt)
            return list(res.scalars().all())
        except Exception as e:
            if settings.ENVIRONMENT != "production":
                logger.warning(f"DB breached sweep failed in dev, falling back to mock: {e}")
                return [
                    a for a in _MOCK_ALERTS_REGISTRY
                    if a.status in ["ACTIVE", "ESCALATED"] and a.timestamp <= sla_cutoff and a.escalation_level == 0
                ]
            raise e

    @staticmethod
    async def query_alerts(
        db: Optional[AsyncSession],
        status_filter: Optional[str] = None,
        severity_filter: Optional[str] = None,
        page: int = 1,
        page_size: int = 50
    ) -> tuple[List[PrioritizedAlertRecord], int]:
        """Query alerts with status/severity filters and return total count for pagination."""
        if db is None:
            filtered = _MOCK_ALERTS_REGISTRY
            if status_filter:
                filtered = [x for x in filtered if x.status.lower() == status_filter.lower()]
            if severity_filter:
                filtered = [x for x in filtered if x.current_severity.lower() == severity_filter.lower()]
            sorted_records = sorted(filtered, key=lambda a: a.priority_score, reverse=True)
            offset = (page - 1) * page_size
            return sorted_records[offset:offset + page_size], len(filtered)

        filter_stmt = select(PrioritizedAlertRecord)
        if status_filter:
            filter_stmt = filter_stmt.where(PrioritizedAlertRecord.status.ilike(status_filter))
        if severity_filter:
            filter_stmt = filter_stmt.where(PrioritizedAlertRecord.current_severity.ilike(severity_filter))

        try:
            # Query total count
            count_stmt = select(func.count()).select_from(filter_stmt.subquery())
            count_res = await db.execute(count_stmt)
            total_count = count_res.scalar_one()

            # Query paginated results
            offset = (page - 1) * page_size
            paginated_stmt = filter_stmt.order_by(PrioritizedAlertRecord.priority_score.desc()).offset(offset).limit(page_size)
            res = await db.execute(paginated_stmt)
            records = list(res.scalars().all())

            if records or total_count > 0:
                return records, total_count
        except Exception as e:
            if settings.ENVIRONMENT != "production":
                logger.warning(f"DB query_alerts failed in dev, falling back to mock: {e}")
                filtered = _MOCK_ALERTS_REGISTRY
                if status_filter:
                    filtered = [x for x in filtered if x.status.lower() == status_filter.lower()]
                if severity_filter:
                    filtered = [x for x in filtered if x.current_severity.lower() == severity_filter.lower()]
                sorted_records = sorted(filtered, key=lambda a: a.priority_score, reverse=True)
                offset = (page - 1) * page_size
                return sorted_records[offset:offset + page_size], len(filtered)
            raise e

        if settings.ENVIRONMENT != "production":
            filtered = _MOCK_ALERTS_REGISTRY
            if status_filter:
                filtered = [x for x in filtered if x.status.lower() == status_filter.lower()]
            if severity_filter:
                filtered = [x for x in filtered if x.current_severity.lower() == severity_filter.lower()]
            sorted_records = sorted(filtered, key=lambda a: a.priority_score, reverse=True)
            offset = (page - 1) * page_size
            return sorted_records[offset:offset + page_size], len(filtered)

        return [], 0

    @staticmethod
    async def save(db: Optional[AsyncSession], alert: PrioritizedAlertRecord) -> PrioritizedAlertRecord:
        """Add and persist a new alert."""
        if db is None:
            _MOCK_ALERTS_REGISTRY.insert(0, alert)
            return alert

        try:
            db.add(alert)
            await db.commit()
            await db.refresh(alert)
            return alert
        except Exception as e:
            await db.rollback()
            if settings.ENVIRONMENT != "production":
                logger.warning(f"DB save failed in dev, falling back to mock save: {e}")
                _MOCK_ALERTS_REGISTRY.insert(0, alert)
                return alert
            raise e

    @staticmethod
    async def commit(db: Optional[AsyncSession]) -> None:
        """Commit current transaction changes."""
        if db is not None:
            await db.commit()


class AlertPrioritizationEngine:
    """Intelligent operational alert prioritization system.

    Supports de-duplication suppression windows, cooldown blocks, and SLA escalation rules.
    """

    @staticmethod
    def calculate_priority_score(
        severity: str,
        score: float,
        occurrences: int,
        escalation: int
    ) -> float:
        """Calculate dynamic alert priority score (0.0 to 100.0).

        Args:
            severity: Anomaly severity string (e.g. CRITICAL).
            score: Anomaly model prediction score.
            occurrences: Duplicate occurrence counter.
            escalation: SLA escalation stage level.

        Returns:
            The calculated priority score between 0.0 and 100.0.
        """
        base_sev = SeverityWeight.get_weight(severity)
        score_weight = score * 30.0
        dup_weight = min(15.0, (occurrences - 1) * 2.0)
        escalation_weight = escalation * 15.0

        return max(0.0, min(100.0, base_sev + score_weight + dup_weight + escalation_weight))

    @staticmethod
    async def inject_and_prioritize_anomaly(
        db: Optional[AsyncSession],
        payload: AnomalyCreate
    ) -> PrioritizedAlertRecord:
        """Processes a newly flagged anomaly trigger.

        Applies de-duplication windows, active cooldown blocks, and priority
        evaluations before persisting.

        Args:
            db: Optional database session.
            payload: Anomaly registration schema payload.

        Returns:
            The newly created or de-duplicated PrioritizedAlertRecord.

        Raises:
            AppHTTPException: If database connection fails.
        """
        now = datetime.utcnow()
        metric = payload.metric_name
        severity = payload.severity.upper()
        anomaly_score = float(payload.score)

        # 1. Cooldown Block Check (last 2 minutes)
        try:
            active_cooldown_alert = await AlertRepository.get_active_cooldown_alert(db, metric, now)
        except Exception as e:
            logger.error(f"Failed to query active cooldown: {e}")
            raise AppHTTPException(
                error_code=ErrorCode.SERVICE_UNAVAILABLE,
                message="Database query failed while fetching alert cooldown.",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            ) from e

        if active_cooldown_alert:
            logger.info(f"Anomaly trigger '{payload.id}' suppressed due to active metric '{metric}' cooldown until {active_cooldown_alert.cooldown_until}")
            suppressed_alert = PrioritizedAlertRecord(
                id=f"alert-sup-{payload.id[:6]}-{int(now.timestamp()) % 10000}",
                anomaly_id=payload.id,
                metric_name=metric,
                original_severity=payload.severity,
                current_severity="LOW",
                priority_score=AlertPrioritizationEngine.calculate_priority_score("LOW", anomaly_score, 1, 0),
                status="SUPPRESSED",
                occurrence_count=1,
                timestamp=now,
                last_occurrence=now,
                cooldown_until=None,
                escalation_level=0,
                description=f"Alert suppressed due to active metric cooldown window. Trigger: {payload.description}"
            )
            try:
                return await AlertRepository.save(db, suppressed_alert)
            except Exception as ex:
                if db is not None:
                    await db.rollback()
                logger.error(f"Failed to persist suppressed alert: {ex}")
                raise AppHTTPException(
                    error_code=ErrorCode.SERVICE_UNAVAILABLE,
                    message="Failed to persist suppressed alert.",
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                ) from ex

        # 2. De-duplication Check (last 5 minutes, status ACTIVE/ESCALATED)
        five_min_ago = now - timedelta(minutes=5)
        try:
            duplicate_alert = await AlertRepository.get_duplicate_alert(db, metric, five_min_ago)
        except Exception as e:
            logger.error(f"Failed duplicate check: {e}")
            raise AppHTTPException(
                error_code=ErrorCode.SERVICE_UNAVAILABLE,
                message="Database duplicate check query failed.",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            ) from e

        if duplicate_alert:
            # Increment occurrence count and merge
            duplicate_alert.occurrence_count += 1
            duplicate_alert.last_occurrence = now
            duplicate_alert.priority_score = AlertPrioritizationEngine.calculate_priority_score(
                duplicate_alert.current_severity,
                anomaly_score,
                duplicate_alert.occurrence_count,
                duplicate_alert.escalation_level
            )
            duplicate_alert.description = f"{duplicate_alert.description} [Merged duplicate incident x{duplicate_alert.occurrence_count}]."
            
            try:
                await AlertRepository.commit(db)
                logger.info(f"Incident '{payload.id}' de-duplicated onto alert '{duplicate_alert.id}' (count={duplicate_alert.occurrence_count})")
                return duplicate_alert
            except Exception as ex:
                if db is not None:
                    await db.rollback()
                logger.error(f"Failed to commit de-duplicated alert: {ex}")
                raise AppHTTPException(
                    error_code=ErrorCode.SERVICE_UNAVAILABLE,
                    message="Failed to update de-duplicated alert.",
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                ) from ex

        # 3. Create a brand new prioritized alert
        p_score = AlertPrioritizationEngine.calculate_priority_score(severity, anomaly_score, 1, 0)
        new_alert = PrioritizedAlertRecord(
            id=f"alert-{payload.id[:6]}-{int(now.timestamp()) % 10000}",
            anomaly_id=payload.id,
            metric_name=metric,
            original_severity=payload.severity,
            current_severity=payload.severity,
            priority_score=p_score,
            status="ACTIVE",
            occurrence_count=1,
            timestamp=now,
            last_occurrence=now,
            cooldown_until=None,
            escalation_level=0,
            description=payload.description
        )

        try:
            new_alert = await AlertRepository.save(db, new_alert)
            logger.info(f"Created prioritized alert '{new_alert.id}' for metric '{metric}' (score={p_score:.1f})")

            # Trigger active notification dispatch
            try:
                from app.services.notification_service import NotificationDeliveryService
                await NotificationDeliveryService.trigger_notifications(db, new_alert)
            except Exception as ne:
                logger.error(f"Failed to trigger notifications for new alert {new_alert.id}: {ne}")

            return new_alert
        except Exception as e:
            if db is not None:
                await db.rollback()
            logger.error(f"Failed to create prioritized alert: {e}")
            raise AppHTTPException(
                error_code=ErrorCode.SERVICE_UNAVAILABLE,
                message="Failed to persist new prioritized alert.",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            ) from e

    @staticmethod
    async def get_prioritized_queue(
        db: Optional[AsyncSession],
        status_filter: Optional[str] = None,
        severity_filter: Optional[str] = None,
        limit: int = 50,
        page: int = 1,
        page_size: int = 50
    ) -> tuple[List[PrioritizedAlertRecord], int]:
        """Retrieves active alerts queue sorted by calculated priority score descending.

        Performs proactive SLA sweeps to trigger escalations for long-standing items.

        Args:
            db: Optional database session.
            status_filter: Optional filter by status (ACTIVE, ESCALATED, etc.).
            severity_filter: Optional filter by current severity.
            limit: Keep for compatibility, but overridden by pagination.
            page: 1-indexed page number.
            page_size: Number of records per page.

        Returns:
            A tuple containing:
              - A list of PrioritizedAlertRecords.
              - The total count of matching alerts.

        Raises:
            AppHTTPException: If database connection fails.
        """
        now = datetime.utcnow()
        # Proactive SLA Sweep: Find alerts active and unacknowledged for >30 seconds
        sla_seconds = AlertConstants.SLA_ESCALATION_SECONDS.value
        sla_cutoff = now - timedelta(seconds=sla_seconds)

        # 1. Proactive SLA Escalation Sweep
        try:
            breached_alerts = await AlertRepository.get_breached_alerts(db, sla_cutoff)
            for alert in breached_alerts:
                alert.escalation_level = 1
                alert.status = "ESCALATED"
                
                # Escalate severity level: LOW -> MEDIUM -> HIGH -> CRITICAL
                sev_hierarchy = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
                curr_idx = sev_hierarchy.index(alert.current_severity.upper()) if alert.current_severity.upper() in sev_hierarchy else 1
                alert.current_severity = sev_hierarchy[min(3, curr_idx + 1)]
                
                # Recalculate priority
                alert.priority_score = AlertPrioritizationEngine.calculate_priority_score(
                    alert.current_severity,
                    0.85,  # default z-score factor
                    alert.occurrence_count,
                    alert.escalation_level
                )
                alert.description = f"{alert.description} [SLA Breach Tier 1: SLA violated. Response exceeded {sla_seconds}s]."

                # Trigger SLA escalation notifications
                try:
                    from app.services.notification_service import NotificationDeliveryService
                    await NotificationDeliveryService.trigger_notifications(db, alert, status_override="ESCALATED")
                except Exception as ne:
                    logger.error(f"Failed to trigger escalation notifications for alert {alert.id}: {ne}")
            
            if breached_alerts:
                await AlertRepository.commit(db)
        except Exception as e:
            logger.error(f"SLA Sweep failed in Postgres: {e}")
            raise AppHTTPException(
                error_code=ErrorCode.SERVICE_UNAVAILABLE,
                message="SLA Escalation Sweep failed.",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            ) from e

        # 2. Query prioritized alerts sorted by priority score descending
        try:
            return await AlertRepository.query_alerts(db, status_filter, severity_filter, page, page_size)
        except Exception as e:
            logger.error(f"Failed to fetch prioritized alerts: {e}")
            raise AppHTTPException(
                error_code=ErrorCode.SERVICE_UNAVAILABLE,
                message="Failed to query prioritized alerts from database.",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            ) from e

    @staticmethod
    async def acknowledge_alert(db: Optional[AsyncSession], alert_id: str) -> PrioritizedAlertRecord:
        """Mark prioritized alert as Acknowledged, entering a 2-minute cooldown window.

        Args:
            db: Optional database session.
            alert_id: Unique alert identifier.

        Returns:
            The acknowledged PrioritizedAlertRecord.

        Raises:
            AppHTTPException: If alert not found or update fails.
        """
        now = datetime.utcnow()
        cooldown_limit = now + timedelta(seconds=AlertConstants.COOLDOWN_SECONDS.value)

        alert = await AlertRepository.get_alert_by_id(db, alert_id)
        if alert is None:
            raise AppHTTPException(
                error_code=ErrorCode.NOT_FOUND,
                message=f"Prioritized alert '{alert_id}' not found.",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        try:
            alert.status = "ACKNOWLEDGED"
            alert.cooldown_until = cooldown_limit
            await AlertRepository.commit(db)
            logger.info(f"Alert '{alert_id}' Acknowledged. Metric '{alert.metric_name}' in cooldown until {cooldown_limit}")
            return alert
        except Exception as e:
            if db is not None:
                await db.rollback()
            logger.error(f"PostgreSQL acknowledge failed for '{alert_id}': {e}")
            raise AppHTTPException(
                error_code=ErrorCode.SERVICE_UNAVAILABLE,
                message="Failed to acknowledge alert due to database error.",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            ) from e

    @staticmethod
    async def resolve_alert(db: Optional[AsyncSession], alert_id: str) -> PrioritizedAlertRecord:
        """Mark prioritized alert as Resolved, entering a 2-minute cooldown window.

        Args:
            db: Optional database session.
            alert_id: Unique alert identifier.

        Returns:
            The resolved PrioritizedAlertRecord.

        Raises:
            AppHTTPException: If alert not found or update fails.
        """
        now = datetime.utcnow()
        cooldown_limit = now + timedelta(seconds=AlertConstants.COOLDOWN_SECONDS.value)

        alert = await AlertRepository.get_alert_by_id(db, alert_id)
        if alert is None:
            raise AppHTTPException(
                error_code=ErrorCode.NOT_FOUND,
                message=f"Prioritized alert '{alert_id}' not found.",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        try:
            alert.status = "RESOLVED"
            alert.cooldown_until = cooldown_limit
            await AlertRepository.commit(db)
            logger.info(f"Alert '{alert_id}' Resolved. Metric '{alert.metric_name}' in cooldown until {cooldown_limit}")

            # Trigger resolution notifications
            try:
                from app.services.notification_service import NotificationDeliveryService
                await NotificationDeliveryService.trigger_notifications(db, alert)
            except Exception as ne:
                logger.error(f"Failed to trigger resolution notifications for alert {alert.id}: {ne}")

            return alert
        except Exception as e:
            if db is not None:
                await db.rollback()
            logger.error(f"PostgreSQL resolution failed for '{alert_id}': {e}")
            raise AppHTTPException(
                error_code=ErrorCode.SERVICE_UNAVAILABLE,
                message="Failed to resolve alert due to database error.",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            ) from e
