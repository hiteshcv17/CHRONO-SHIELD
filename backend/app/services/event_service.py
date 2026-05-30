import enum
from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import AnomalyEvent, SeverityLevel


class EventService:
    """Encapsulates anomaly event lifecycle operations.

    - creation with severity and optional metadata
    - status updates (open, acknowledged, resolved, expired)
    - automatic expiration based on a configurable TTL
    - queries for active/open events
    """

    def __init__(self, ttl_hours: int = 24):
        self.ttl = timedelta(hours=ttl_hours)

    async def create_event(
        self,
        db: AsyncSession,
        description: str,
        severity: SeverityLevel = SeverityLevel.LOW,
        metadata: Optional[str] = None,
    ) -> AnomalyEvent:
        """Persist a new :class:`AnomalyEvent`.

        Args:
            db: Async DB session.
            description: Human‑readable description of the anomaly.
            severity: One of the predefined severity levels.
            metadata: Optional JSON string with extra context.
        """
        new_event = AnomalyEvent(
            description=description,
            severity=severity,
            timestamp=datetime.utcnow(),
            lifecycle_status="open",
            metadata=metadata,
        )
        db.add(new_event)
        await db.commit()
        await db.refresh(new_event)
        return new_event

    async def list_open_events(self, db: AsyncSession) -> List[AnomalyEvent]:
        """Return all events whose status is ``open`` or ``acknowledged``."""
        stmt = select(AnomalyEvent).where(
            AnomalyEvent.lifecycle_status.in_(["open", "acknowledged"])
        )
        result = await db.execute(stmt)
        return result.scalars().all()

    async def update_status(
        self,
        db: AsyncSession,
        event_id: int,
        new_status: str,
    ) -> Optional[AnomalyEvent]:
        """Change the lifecycle_status of an event.

        Returns the updated event or ``None`` if not found.
        """
        stmt = (
            update(AnomalyEvent)
            .where(AnomalyEvent.id == event_id)
            .values(lifecycle_status=new_status)
            .execution_options(synchronize_session="fetch")
        )
        await db.execute(stmt)
        await db.commit()
        # Fetch the updated row
        stmt = select(AnomalyEvent).where(AnomalyEvent.id == event_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def purge_expired(self, db: AsyncSession) -> int:
        """Delete events older than the TTL.

        Returns the number of rows removed.
        """
        expiry_time = datetime.utcnow() - self.ttl
        stmt = delete(AnomalyEvent).where(AnomalyEvent.timestamp < expiry_time)
        result = await db.execute(stmt)
        await db.commit()
        return result.rowcount

    async def get_event(
        self, db: AsyncSession, event_id: int
    ) -> Optional[AnomalyEvent]:
        stmt = select(AnomalyEvent).where(AnomalyEvent.id == event_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
