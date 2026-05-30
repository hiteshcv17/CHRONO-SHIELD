import pytest
import asyncio
from datetime import datetime, timedelta
from app.services.alert_service import AlertPrioritizationEngine
from app.schemas.anomaly import AnomalyCreate


class TestAlertPrioritization:

    def test_priority_score_calculation(self):
        """Assert priority scoring yields valid normalizations [0 - 100] across severities."""
        # Critical high z-score base
        score = AlertPrioritizationEngine.calculate_priority_score(
            "CRITICAL", 0.95, 1, 0
        )
        # 40 + 0.95 * 30 = 68.5
        assert pytest.approx(score) == 68.5

        # Critical escalated duplicate
        score = AlertPrioritizationEngine.calculate_priority_score(
            "CRITICAL", 0.95, 3, 1
        )
        # 40 + 0.95 * 30 + (3-1)*2 + 15 = 40 + 28.5 + 4 + 15 = 87.5
        assert pytest.approx(score) == 87.5

        # Bounding limits
        max_score = AlertPrioritizationEngine.calculate_priority_score(
            "CRITICAL", 1.0, 50, 5
        )
        assert max_score == 100.0

    def test_in_memory_cooldown_suppression(self):
        """Assert dynamic injection suppression during active cooldown clocks."""
        import asyncio

        async def run_test():
            # Inject a manual resolved/acknowledged alert with a future cooldown limit
            now = datetime.utcnow()
            payload1 = AnomalyCreate(
                id="anom-test-cd-1",
                timestamp=now,
                metric_name="temp_metric_cd",
                severity="CRITICAL",
                score=0.9,
                description="Test cooldown source trigger.",
            )
            # Inject new prioritized alert
            alert = await AlertPrioritizationEngine.inject_and_prioritize_anomaly(
                None, payload1
            )
            assert alert.status == "ACTIVE"

            # Acknowledge to initiate cooldown lock
            acknowledged = await AlertPrioritizationEngine.acknowledge_alert(
                None, alert.id
            )
            assert acknowledged.status == "ACKNOWLEDGED"
            assert acknowledged.cooldown_until > now

            # Inject a duplicate during the active cooldown lock
            payload2 = AnomalyCreate(
                id="anom-test-cd-2",
                timestamp=now,
                metric_name="temp_metric_cd",
                severity="CRITICAL",
                score=0.8,
                description="Duplicate cooldown source trigger.",
            )
            suppressed = await AlertPrioritizationEngine.inject_and_prioritize_anomaly(
                None, payload2
            )
            assert suppressed.status == "SUPPRESSED"
            assert (
                "suppressed due to active metric cooldown"
                in suppressed.description.lower()
            )

        asyncio.run(run_test())

    def test_in_memory_duplicate_merging(self):
        """Assert parallel duplicate incidents merge and increment occurrence counts."""
        import asyncio

        async def run_test():
            now = datetime.utcnow()
            payload1 = AnomalyCreate(
                id="anom-test-dup-1",
                timestamp=now,
                metric_name="temp_metric_dup",
                severity="CRITICAL",
                score=0.9,
                description="Original alert.",
            )
            alert = await AlertPrioritizationEngine.inject_and_prioritize_anomaly(
                None, payload1
            )
            assert alert.status == "ACTIVE"
            assert alert.occurrence_count == 1

            # Inject duplicate within 5-minute de-duplication window
            payload2 = AnomalyCreate(
                id="anom-test-dup-2",
                timestamp=now,
                metric_name="temp_metric_dup",
                severity="CRITICAL",
                score=0.9,
                description="Duplicate alert.",
            )
            merged = await AlertPrioritizationEngine.inject_and_prioritize_anomaly(
                None, payload2
            )
            assert merged.id == alert.id
            assert merged.occurrence_count == 2
            assert "merged duplicate" in merged.description.lower()

        asyncio.run(run_test())


class TestAlertAPI:

    @classmethod
    def setup_class(cls):
        import asyncio

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        from fastapi.testclient import TestClient
        from app.main import app

        cls.client = TestClient(app)

        # Seed test alerts to ensure database state is correct for self-contained testing
        from app.db.session import async_session_factory
        from app.models.alert import PrioritizedAlertRecord
        from sqlalchemy import select

        async def seed_test_alerts():
            from app.db.session import engine
            from app.models.base import Base
            from app.models.anomaly import AnomalyRecord  # noqa: F401
            from app.models.weather import WeatherRecordModel  # noqa: F401
            from app.models.traffic import TrafficRecordModel  # noqa: F401
            from app.models.energy import EnergyRecordModel  # noqa: F401
            from app.models.social import SocialComplaintRecord  # noqa: F401
            from app.models.user import User  # noqa: F401
            from app.models.notification import (  # noqa: F401
                NotificationChannelConfig,
                NotificationDeliveryLog,
            )
            from app.models.report import Report  # noqa: F401
            from app.models.asset import Asset  # noqa: F401
            from app.models.system_setting import SystemSetting  # noqa: F401

            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            async with async_session_factory() as session:
                alert_a = PrioritizedAlertRecord(
                    id="alert-001",
                    anomaly_id="anom-test-001",
                    metric_name="CPU_Usage",
                    original_severity="CRITICAL",
                    current_severity="CRITICAL",
                    priority_score=85.0,
                    status="ACTIVE",
                    occurrence_count=3,
                    timestamp=datetime.utcnow() - timedelta(seconds=45),
                    last_occurrence=datetime.utcnow() - timedelta(seconds=10),
                    cooldown_until=None,
                    escalation_level=0,
                    description="Test CPU spike description.",
                )
                alert_b = PrioritizedAlertRecord(
                    id="alert-002",
                    anomaly_id="anom-test-002",
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
                    description="Test latency description.",
                )
                for alert in [alert_a, alert_b]:
                    stmt = select(PrioritizedAlertRecord).where(
                        PrioritizedAlertRecord.id == alert.id
                    )
                    res = await session.execute(stmt)
                    if not res.scalar_one_or_none():
                        session.add(alert)
                await session.commit()

        loop.run_until_complete(seed_test_alerts())

    def test_get_alerts_queue_api(self):
        """Assert GET /api/v1/alerts/queue returns prioritized logs in order of priority scores."""
        response = self.client.get("/api/v1/alerts/queue")
        assert response.status_code == 200
        envelope = response.json()
        assert "items" in envelope
        data = envelope["items"]
        assert len(data) >= 2

        # Verify sorted order descending
        scores = [a["priority_score"] for a in data]
        assert scores == sorted(scores, reverse=True)

        for alert in data:
            assert "id" in alert
            assert "anomaly_id" in alert
            assert "metric_name" in alert
            assert "priority_score" in alert
            assert "status" in alert
            assert alert["status"] in [
                "ACTIVE",
                "ACKNOWLEDGED",
                "SUPPRESSED",
                "ESCALATED",
                "RESOLVED",
            ]

    def test_alert_acknowledge_and_resolve_api(self):
        """Assert PUT acknowledge and resolve routes execute and persist successfully."""
        # Step 1: Acknowledge alert-001
        response = self.client.put("/api/v1/alerts/alert-001/acknowledge")
        assert response.status_code == 200
        envelope = response.json()
        assert envelope["success"] is True
        data = envelope["data"]
        assert data["id"] == "alert-001"
        assert data["status"] == "ACKNOWLEDGED"
        assert data["cooldown_until"] is not None

        # Step 2: Resolve alert-001
        response = self.client.put("/api/v1/alerts/alert-001/resolve")
        assert response.status_code == 200
        envelope = response.json()
        assert envelope["success"] is True
        data = envelope["data"]
        assert data["id"] == "alert-001"
        assert data["status"] == "RESOLVED"
