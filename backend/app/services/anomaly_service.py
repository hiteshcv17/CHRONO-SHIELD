import logging
from typing import Any, List, Optional
from datetime import datetime, timedelta
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.anomaly import AnomalyCreate, AnomalyUpdate
from app.models.anomaly import AnomalyRecord
from app.core.exceptions import AppHTTPException, ErrorCode
from app.configs.settings import settings
from fastapi import status

logger = logging.getLogger("anomaly_service")

# Standard in-memory array to serve as fallback in development or testing
_MOCK_REGISTRY: List[AnomalyRecord] = [
    AnomalyRecord(
        id="anom-098",
        timestamp=datetime.utcnow() - timedelta(minutes=14),
        metric_name="CPU_Usage",
        severity="CRITICAL",
        score=0.942,
        description="CPU load spiked anomalously beyond standard weekly deviation threshold.",
        acknowledged=False
    ),
    AnomalyRecord(
        id="anom-099",
        timestamp=datetime.utcnow() - timedelta(minutes=4),
        metric_name="Database_Latency",
        severity="WARNING",
        score=0.814,
        description="Connection pool saturation detected triggering high-percentile transaction delays.",
        acknowledged=True
    )
]


class AnomalyService:
    """Decoupled service handling data validations and query translations.

    Optimized for transactional robustness with direct PostgreSQL persistence.
    """

    @staticmethod
    async def _execute_query(db: AsyncSession, stmt) -> Any:
        """Helper to execute DB queries and raise standard service errors on failure."""
        try:
            result = await db.execute(stmt)
            return result
        except Exception as e:
            logger.error(f"Database operation failed: {e}")
            raise AppHTTPException(
                error_code=ErrorCode.SERVICE_UNAVAILABLE,
                message="The database service is currently unavailable. Please try again later.",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            ) from e

    @staticmethod
    async def get_anomaly_by_id(db: AsyncSession, anomaly_id: str) -> Optional[AnomalyRecord]:
        """Locates single incident records matching unique IDs.

        Args:
            db: Active database session.
            anomaly_id: Unique anomaly identifier.

        Returns:
            The AnomalyRecord if found, otherwise None.

        Raises:
            AppHTTPException: If database connection fails.
        """
        if db is None:
            matches = [x for x in _MOCK_REGISTRY if x.id == anomaly_id]
            return matches[0] if matches else None

        stmt = select(AnomalyRecord).where(AnomalyRecord.id == anomaly_id)
        try:
            result = await db.execute(stmt)
            record = result.scalar_one_or_none()
            if record is not None:
                return record
        except Exception as e:
            if settings.ENVIRONMENT != "production":
                logger.warning(f"DB failed in dev mode, falling back to mock: {e}")
                matches = [x for x in _MOCK_REGISTRY if x.id == anomaly_id]
                return matches[0] if matches else None
            logger.error(f"Database operation failed: {e}")
            raise AppHTTPException(
                error_code=ErrorCode.SERVICE_UNAVAILABLE,
                message="The database service is currently unavailable. Please try again later.",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            ) from e

        if settings.ENVIRONMENT != "production":
            matches = [x for x in _MOCK_REGISTRY if x.id == anomaly_id]
            if matches:
                return matches[0]

        return None

    @staticmethod
    async def query_anomalies(
        db: AsyncSession, 
        metric: Optional[str] = None, 
        severity: Optional[str] = None, 
        limit: int = 50
    ) -> List[AnomalyRecord]:
        """Retrieves logs of anomalies matching search filters.

        Args:
            db: Active database session.
            metric: Optional metric label filter (e.g. CPU_Usage).
            severity: Optional severity filter (e.g. CRITICAL).
            limit: Page size threshold limit.

        Returns:
            A list of matching AnomalyRecords.

        Raises:
            AppHTTPException: If database operation fails.
        """
        if db is None:
            filtered = _MOCK_REGISTRY
            if metric:
                filtered = [x for x in filtered if x.metric_name.lower() == metric.lower()]
            if severity:
                filtered = [x for x in filtered if x.severity.upper() == severity.upper()]
            return filtered[:limit]

        stmt = select(AnomalyRecord)
        if metric:
            stmt = stmt.where(AnomalyRecord.metric_name.ilike(metric))
        if severity:
            stmt = stmt.where(AnomalyRecord.severity.ilike(severity))
        stmt = stmt.order_by(AnomalyRecord.timestamp.desc()).limit(limit)

        try:
            result = await db.execute(stmt)
            records = list(result.scalars().all())
            if records:
                return records
        except Exception as e:
            if settings.ENVIRONMENT != "production":
                logger.warning(f"DB query failed in dev mode, falling back to mock: {e}")
                filtered = _MOCK_REGISTRY
                if metric:
                    filtered = [x for x in filtered if x.metric_name.lower() == metric.lower()]
                if severity:
                    filtered = [x for x in filtered if x.severity.upper() == severity.upper()]
                return filtered[:limit]
            logger.error(f"Database operation failed: {e}")
            raise AppHTTPException(
                error_code=ErrorCode.SERVICE_UNAVAILABLE,
                message="The database service is currently unavailable. Please try again later.",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            ) from e

        if settings.ENVIRONMENT != "production":
            filtered = _MOCK_REGISTRY
            if metric:
                filtered = [x for x in filtered if x.metric_name.lower() == metric.lower()]
            if severity:
                filtered = [x for x in filtered if x.severity.upper() == severity.upper()]
            return filtered[:limit]

        return []

    @staticmethod
    async def query_anomalies_paginated(
        db: AsyncSession, 
        metric: Optional[str] = None, 
        severity: Optional[str] = None, 
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[List[AnomalyRecord], int]:
        """Retrieves logs of anomalies matching search filters with pagination.

        Args:
            db: Active database session.
            metric: Optional metric label filter (e.g. CPU_Usage).
            severity: Optional severity filter (e.g. CRITICAL).
            page: 1-indexed page number.
            page_size: Number of records per page.

        Returns:
            A tuple containing:
              - A list of matching AnomalyRecords for the current page.
              - The total count of matching records across all pages.

        Raises:
            AppHTTPException: If database operation fails.
        """
        if db is None:
            filtered = _MOCK_REGISTRY
            if metric:
                filtered = [x for x in filtered if x.metric_name.lower() == metric.lower()]
            if severity:
                filtered = [x for x in filtered if x.severity.upper() == severity.upper()]
            total_count = len(filtered)
            offset = (page - 1) * page_size
            return filtered[offset:offset + page_size], total_count

        # Build base filter query
        filter_stmt = select(AnomalyRecord)
        if metric:
            filter_stmt = filter_stmt.where(AnomalyRecord.metric_name.ilike(metric))
        if severity:
            filter_stmt = filter_stmt.where(AnomalyRecord.severity.ilike(severity))

        try:
            # Query total count
            count_stmt = select(func.count()).select_from(filter_stmt.subquery())
            count_result = await db.execute(count_stmt)
            total_count = count_result.scalar_one()

            # Query paginated records
            offset = (page - 1) * page_size
            paginated_stmt = filter_stmt.order_by(AnomalyRecord.timestamp.desc()).offset(offset).limit(page_size)
            result = await db.execute(paginated_stmt)
            records = list(result.scalars().all())
            
            if records or total_count > 0:
                return records, total_count
        except Exception as e:
            if settings.ENVIRONMENT != "production":
                logger.warning(f"DB paginated query failed in dev mode, falling back to mock: {e}")
                filtered = _MOCK_REGISTRY
                if metric:
                    filtered = [x for x in filtered if x.metric_name.lower() == metric.lower()]
                if severity:
                    filtered = [x for x in filtered if x.severity.upper() == severity.upper()]
                total_count = len(filtered)
                offset = (page - 1) * page_size
                return filtered[offset:offset + page_size], total_count
            logger.error(f"Database operation failed: {e}")
            raise AppHTTPException(
                error_code=ErrorCode.SERVICE_UNAVAILABLE,
                message="The database service is currently unavailable. Please try again later.",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            ) from e

        if settings.ENVIRONMENT != "production":
            filtered = _MOCK_REGISTRY
            if metric:
                filtered = [x for x in filtered if x.metric_name.lower() == metric.lower()]
            if severity:
                filtered = [x for x in filtered if x.severity.upper() == severity.upper()]
            total_count = len(filtered)
            offset = (page - 1) * page_size
            return filtered[offset:offset + page_size], total_count

        return [], 0

    @staticmethod
    async def insert_anomaly(db: AsyncSession, payload: AnomalyCreate) -> AnomalyRecord:
        """Creates and inserts custom anomaly signatures.

        Args:
            db: Active database session.
            payload: Pydantic creation schema.

        Returns:
            The created and persisted AnomalyRecord.

        Raises:
            AppHTTPException: If duplicate ID is provided or DB write fails.
        """
        # Move duplicate-existence checks from routes to service layer
        existing = await AnomalyService.get_anomaly_by_id(db, payload.id)
        if existing:
            raise AppHTTPException(
                error_code=ErrorCode.ALREADY_EXISTS,
                message=f"Incident record with ID '{payload.id}' already exists.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        new_record = AnomalyRecord(
            id=payload.id,
            timestamp=payload.timestamp,
            metric_name=payload.metric_name,
            severity=payload.severity,
            score=payload.score,
            description=payload.description,
            acknowledged=False
        )
        
        if db is None:
            _MOCK_REGISTRY.insert(0, new_record)
            return new_record

        try:
            db.add(new_record)
            await db.commit()
            await db.refresh(new_record)
            logger.info(f"Successfully persisted anomaly event '{payload.id}' to database.")
            return new_record
        except Exception as e:
            await db.rollback()
            if settings.ENVIRONMENT != "production":
                logger.warning(f"DB insert failed in dev mode, falling back to mock insert: {e}")
                _MOCK_REGISTRY.insert(0, new_record)
                return new_record
            logger.error(f"Database insert failed for anomaly '{payload.id}': {e}")
            raise AppHTTPException(
                error_code=ErrorCode.SERVICE_UNAVAILABLE,
                message="Failed to persist anomaly record due to DB error.",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            ) from e

    @staticmethod
    async def update_anomaly(db: AsyncSession, anomaly_id: str, payload: AnomalyUpdate) -> AnomalyRecord:
        """Updates the acknowledgement state of incident signals.

        Args:
            db: Active database session.
            anomaly_id: Unique anomaly identifier.
            payload: Pydantic update schema.

        Returns:
            The updated AnomalyRecord.

        Raises:
            AppHTTPException: If anomaly record is not found or DB update fails.
        """
        if db is None:
            for record in _MOCK_REGISTRY:
                if record.id == anomaly_id:
                    record.acknowledged = payload.acknowledged
                    return record
            raise AppHTTPException(
                error_code=ErrorCode.NOT_FOUND,
                message=f"No active anomaly registry found matching ID '{anomaly_id}'",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        record = await AnomalyService.get_anomaly_by_id(db, anomaly_id)
        if record is None:
            raise AppHTTPException(
                error_code=ErrorCode.NOT_FOUND,
                message=f"No active anomaly registry found matching ID '{anomaly_id}'",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        try:
            record.acknowledged = payload.acknowledged
            await db.commit()
            await db.refresh(record)
            logger.info(f"Successfully updated acknowledgement for anomaly '{anomaly_id}'.")
            return record
        except Exception as e:
            await db.rollback()
            if settings.ENVIRONMENT != "production":
                logger.warning(f"DB update failed in dev mode, falling back to mock update: {e}")
                for record in _MOCK_REGISTRY:
                    if record.id == anomaly_id:
                        record.acknowledged = payload.acknowledged
                        return record
            logger.error(f"Database update failed for anomaly '{anomaly_id}': {e}")
            raise AppHTTPException(
                error_code=ErrorCode.SERVICE_UNAVAILABLE,
                message="Failed to update anomaly acknowledgement due to DB error.",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            ) from e
