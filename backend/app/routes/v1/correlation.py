from fastapi import APIRouter, Query, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from app.db.session import get_db_session
from app.schemas.correlation import (
    CorrelationMatrixResponse,
    CorrelationGraphResponse,
    TimeOverlayResponse,
    ActivityIntensityResponse,
    AnomalyConcentrationResponse,
    SynchronizedAnomaliesResponse,
    LagAnalysisResponse,
)
from app.services.correlation_service import CorrelationService
from app.utils.cache import cache_response
from app.utils.constants import CacheTTL

from app.core.auth import require_analyst

router = APIRouter(dependencies=[Depends(require_analyst)])


@router.get(
    "/matrix",
    response_model=CorrelationMatrixResponse,
    status_code=status.HTTP_200_OK,
    summary="Compute bivariate telemetry correlation matrix",
)
@cache_response(ttl=CacheTTL.CORRELATION.value, prefix="correlation")
async def get_correlation_matrix(
    city: str = Query("New York", description="Target city for cross-source analysis"),
    window_days: Optional[int] = Query(
        None, description="Rolling time filter window in days (e.g. 1, 7, 30)"
    ),
    db: AsyncSession = Depends(get_db_session),
) -> CorrelationMatrixResponse:
    """
    Computes Pearson correlation coefficients for all cross-source metrics, including rolling windowing.
    """
    variables, matrix = await CorrelationService.get_correlation_matrix(
        db, city, window_days
    )
    return CorrelationMatrixResponse(success=True, variables=variables, matrix=matrix)


@router.get(
    "/graph",
    response_model=CorrelationGraphResponse,
    status_code=status.HTTP_200_OK,
    summary="Get cross-source relationship nodes and edges",
)
@cache_response(ttl=CacheTTL.CORRELATION.value, prefix="correlation")
async def get_correlation_graph(
    city: str = Query("New York", description="Target city for relationship mapping"),
    threshold: float = Query(
        0.3, ge=0.0, le=1.0, description="Minimum correlation filter threshold"
    ),
    window_days: Optional[int] = Query(
        None, description="Rolling time filter window in days (e.g. 1, 7, 30)"
    ),
    db: AsyncSession = Depends(get_db_session),
) -> CorrelationGraphResponse:
    """
    Returns graph representation of metrics correlated above the specified coefficient threshold, supporting rolling window filters.
    """
    nodes, edges = await CorrelationService.get_correlation_graph(
        db, city, threshold, window_days
    )
    return CorrelationGraphResponse(success=True, nodes=nodes, edges=edges)


@router.get(
    "/overlays",
    response_model=TimeOverlayResponse,
    status_code=status.HTTP_200_OK,
    summary="Fetch synchronized multi-variable timeline arrays",
)
@cache_response(ttl=CacheTTL.CORRELATION.value, prefix="correlation")
async def get_time_overlays(
    city: str = Query("New York", description="Target city for timelines alignment"),
    window_days: Optional[int] = Query(
        None, description="Rolling time filter window in days (e.g. 1, 7, 30)"
    ),
    db: AsyncSession = Depends(get_db_session),
) -> TimeOverlayResponse:
    """
    Aligns chronological weather, traffic, energy, AI anomaly, and complaints streams into a single dataset.
    """
    timestamps, series = await CorrelationService.get_aligned_dataframe(
        db, city, window_days
    )
    return TimeOverlayResponse(success=True, timestamps=timestamps, series=series)


@router.get(
    "/intensity",
    response_model=ActivityIntensityResponse,
    status_code=status.HTTP_200_OK,
    summary="Compute DOW vs Hour activity intensity grid",
)
@cache_response(ttl=CacheTTL.CORRELATION.value, prefix="correlation")
async def get_activity_intensity(
    city: str = Query("New York", description="Target city for activity matrix"),
    db: AsyncSession = Depends(get_db_session),
) -> ActivityIntensityResponse:
    """
    Returns 24x7 matrix representing peak usage/congestion patterns.
    """
    days, hours, matrix = await CorrelationService.get_activity_intensity(db, city)
    return ActivityIntensityResponse(
        success=True, days=days, hours=hours, matrix=matrix
    )


@router.get(
    "/concentration",
    response_model=AnomalyConcentrationResponse,
    status_code=status.HTTP_200_OK,
    summary="Compute DOW vs Hour anomaly concentration grid",
)
@cache_response(ttl=CacheTTL.CORRELATION.value, prefix="correlation")
async def get_anomaly_concentration(
    city: str = Query("New York", description="Target city for anomaly hotspots"),
    db: AsyncSession = Depends(get_db_session),
) -> AnomalyConcentrationResponse:
    """
    Returns 24x7 anomaly occurrence count matrix to highlight threat windows.
    """
    days, hours, matrix = await CorrelationService.get_anomaly_concentration(db, city)
    return AnomalyConcentrationResponse(
        success=True, days=days, hours=hours, matrix=matrix
    )


@router.get(
    "/synchronized-anomalies",
    response_model=SynchronizedAnomaliesResponse,
    status_code=status.HTTP_200_OK,
    summary="Detect concurrent anomaly spikes across sources",
)
@cache_response(ttl=CacheTTL.CORRELATION.value, prefix="correlation")
async def get_synchronized_anomalies(
    city: str = Query("New York", description="Target city for synchronized anomalies"),
    db: AsyncSession = Depends(get_db_session),
) -> SynchronizedAnomaliesResponse:
    """
    Scans aligned datasets to return a list of concurrent failure events across weather, traffic, and complaints.
    """
    anomalies = await CorrelationService.get_synchronized_anomalies(db, city)
    return SynchronizedAnomaliesResponse(success=True, anomalies=anomalies)


@router.get(
    "/lag-analysis",
    response_model=LagAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Calculate optimal temporal lags and cascade relationships",
)
@cache_response(ttl=CacheTTL.CORRELATION.value, prefix="correlation")
async def get_lag_analysis(
    city: str = Query("New York", description="Target city for lag cross-correlations"),
    db: AsyncSession = Depends(get_db_session),
) -> LagAnalysisResponse:
    """
    Evaluates correlation coefficients at different temporal offsets to map leading/lagging relationships.
    """
    relationships = await CorrelationService.get_lag_relationships(db, city)
    return LagAnalysisResponse(success=True, relationships=relationships)
