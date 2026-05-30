import asyncio
import logging
import sys
import os
from datetime import datetime, timedelta

# Add backend directory to PYTHONPATH
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.db.session import async_session_factory, engine
from app.models.anomaly import AnomalyRecord
from app.models.alert import PrioritizedAlertRecord
from sqlalchemy import select

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seeder")


async def seed_data():
    logger.info("Starting demo data seeding...")
    async with async_session_factory() as session:
        # 1. Seed demo anomalies
        anom_1 = AnomalyRecord(
            id="anom-098",
            timestamp=datetime.utcnow() - timedelta(minutes=14),
            metric_name="CPU_Usage",
            severity="CRITICAL",
            score=0.942,
            description="CPU load spiked anomalously beyond standard weekly deviation threshold.",
            acknowledged=False
        )
        anom_2 = AnomalyRecord(
            id="anom-099",
            timestamp=datetime.utcnow() - timedelta(minutes=4),
            metric_name="Database_Latency",
            severity="WARNING",
            score=0.814,
            description="Connection pool saturation detected triggering high-percentile transaction delays.",
            acknowledged=True
        )

        for anom in [anom_1, anom_2]:
            stmt = select(AnomalyRecord).where(AnomalyRecord.id == anom.id)
            res = await session.execute(stmt)
            if not res.scalar_one_or_none():
                session.add(anom)
                logger.info(f"Seeded anomaly: {anom.id}")

        # 2. Seed demo alerts
        alert_1 = PrioritizedAlertRecord(
            id="alert-001",
            anomaly_id="anom-098",
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
            description="CPU load spiked anomalously beyond standard weekly deviation threshold."
        )
        alert_2 = PrioritizedAlertRecord(
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

        for alert in [alert_1, alert_2]:
            stmt = select(PrioritizedAlertRecord).where(PrioritizedAlertRecord.id == alert.id)
            res = await session.execute(stmt)
            if not res.scalar_one_or_none():
                session.add(alert)
                logger.info(f"Seeded alert: {alert.id}")

        await session.commit()
    logger.info("Demo data seeding completed successfully.")


if __name__ == "__main__":
    asyncio.run(seed_data())
