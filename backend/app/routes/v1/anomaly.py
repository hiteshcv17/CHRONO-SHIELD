from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db_session
from app.schemas.anomaly import AnomalyCreate, AnomalyResponse, AnomalyUpdate
from app.services.anomaly_service import AnomalyService
from app.utils.cache import cache_response, invalidate_cache_by_pattern
from app.core.auth import get_current_user
from app.core.base import ApiResponse, PaginatedResponse
from app.utils.constants import CacheTTL, PaginationDefaults

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("/", response_model=PaginatedResponse[AnomalyResponse], status_code=status.HTTP_200_OK)
@cache_response(ttl=CacheTTL.ANOMALIES.value, prefix="anomalies")
async def fetch_anomalies(
    metric: Optional[str] = Query(None, max_length=100, description="Filter incidents by metric label (e.g. CPU_Usage)"),
    severity: Optional[str] = Query(None, description="Filter incidents by severity (CRITICAL, WARNING)"),
    page: int = Query(PaginationDefaults.PAGE.value, ge=1, description="Page number"),
    page_size: int = Query(PaginationDefaults.PAGE_SIZE.value, ge=1, le=PaginationDefaults.MAX_PAGE_SIZE.value, description="Records per page"),
    db: AsyncSession = Depends(get_db_session)
) -> PaginatedResponse[AnomalyResponse]:
    """
    Query historical temporal anomalies matching specific filter thresholds with pagination.
    """
    records, total = await AnomalyService.query_anomalies_paginated(
        db, metric=metric, severity=severity, page=page, page_size=page_size
    )
    items = [AnomalyResponse.model_validate(r) for r in records]
    return PaginatedResponse.build(items=items, total=total, page=page, page_size=page_size)


@router.post("/", response_model=ApiResponse[AnomalyResponse], status_code=status.HTTP_201_CREATED)
async def register_anomaly(
    payload: AnomalyCreate,
    db: AsyncSession = Depends(get_db_session)
) -> ApiResponse[AnomalyResponse]:
    """
    Inject or record a newly flagged anomaly from automated ML pipelines.
    """
    res = await AnomalyService.insert_anomaly(db, payload)
    await invalidate_cache_by_pattern("anomalies:*")
    await invalidate_cache_by_pattern("health:*")
    await invalidate_cache_by_pattern("correlation:*")
    return ApiResponse.ok(res)


@router.put("/{anomaly_id}", response_model=ApiResponse[AnomalyResponse], status_code=status.HTTP_200_OK)
async def update_anomaly_status(
    anomaly_id: str,
    payload: AnomalyUpdate,
    db: AsyncSession = Depends(get_db_session)
) -> ApiResponse[AnomalyResponse]:
    """
    Acknowledge or mitigate a specific incident alert.
    """
    res = await AnomalyService.update_anomaly(db, anomaly_id, payload)
    await invalidate_cache_by_pattern("anomalies:*")
    await invalidate_cache_by_pattern("health:*")
    await invalidate_cache_by_pattern("correlation:*")
    return ApiResponse.ok(res)
