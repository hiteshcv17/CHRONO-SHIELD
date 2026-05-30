from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db_session
from app.schemas.alert import PrioritizedAlertResponse
from app.schemas.anomaly import AnomalyCreate
from app.services.alert_service import AlertPrioritizationEngine
from app.core.auth import require_analyst
from app.core.base import ApiResponse, PaginatedResponse
from app.utils.constants import PaginationDefaults

router = APIRouter(dependencies=[Depends(require_analyst)])


@router.get(
    "/queue",
    response_model=PaginatedResponse[PrioritizedAlertResponse],
    status_code=status.HTTP_200_OK,
)
async def fetch_alert_queue(
    status_filter: Optional[str] = Query(
        None,
        description="Filter queue by status (ACTIVE, ACKNOWLEDGED, SUPPRESSED, ESCALATED, RESOLVED)",
    ),
    severity: Optional[str] = Query(
        None, description="Filter queue by severity (CRITICAL, HIGH, MEDIUM, LOW)"
    ),
    page: int = Query(PaginationDefaults.PAGE.value, ge=1, description="Page number"),
    page_size: int = Query(
        PaginationDefaults.PAGE_SIZE.value,
        ge=1,
        le=PaginationDefaults.MAX_PAGE_SIZE.value,
        description="Records per page",
    ),
    db: AsyncSession = Depends(get_db_session),
) -> PaginatedResponse[PrioritizedAlertResponse]:
    """
    Get active prioritized alert queue sorted by dynamic priority score descending.
    Sweeps unacknowledged SLA response time breaches dynamically.
    """
    records, total = await AlertPrioritizationEngine.get_prioritized_queue(
        db,
        status_filter=status_filter,
        severity_filter=severity,
        page=page,
        page_size=page_size,
    )
    return PaginatedResponse.build(
        items=records, total=total, page=page, page_size=page_size
    )


@router.post(
    "/inject",
    response_model=ApiResponse[PrioritizedAlertResponse],
    status_code=status.HTTP_201_CREATED,
)
async def inject_prioritized_incident(
    payload: AnomalyCreate, db: AsyncSession = Depends(get_db_session)
) -> ApiResponse[PrioritizedAlertResponse]:
    """
    Manually inject an anomaly that runs through the de-duplication,
    cooldown check, and priority scoring engine.
    """
    res = await AlertPrioritizationEngine.inject_and_prioritize_anomaly(db, payload)
    return ApiResponse.ok(res)


@router.put(
    "/{alert_id}/acknowledge",
    response_model=ApiResponse[PrioritizedAlertResponse],
    status_code=status.HTTP_200_OK,
)
async def acknowledge_prioritized_alert(
    alert_id: str, db: AsyncSession = Depends(get_db_session)
) -> ApiResponse[PrioritizedAlertResponse]:
    """
    Acknowledge an active or escalated alert, initiating a 2-minute cooldown block on its metric.
    """
    res = await AlertPrioritizationEngine.acknowledge_alert(db, alert_id)
    return ApiResponse.ok(res)


@router.put(
    "/{alert_id}/resolve",
    response_model=ApiResponse[PrioritizedAlertResponse],
    status_code=status.HTTP_200_OK,
)
async def resolve_prioritized_alert(
    alert_id: str, db: AsyncSession = Depends(get_db_session)
) -> ApiResponse[PrioritizedAlertResponse]:
    """
    Resolve a prioritized alert, initiating a 2-minute cooldown block on its metric.
    """
    res = await AlertPrioritizationEngine.resolve_alert(db, alert_id)
    return ApiResponse.ok(res)
