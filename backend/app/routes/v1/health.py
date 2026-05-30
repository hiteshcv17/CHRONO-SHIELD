from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db_session
from app.schemas.health import InfrastructureHealthResponse, CityHealthResponse
from app.services.health_service import HealthService
from app.utils.cache import cache_response
from app.utils.constants import CacheTTL

from app.core.auth import get_current_user

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get(
    "/diagnose",
    response_model=InfrastructureHealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Compute predictive infrastructure health diagnostics and failure probabilities",
)
@cache_response(ttl=CacheTTL.HEALTH.value, prefix="health")
async def get_infrastructure_diagnostics(
    db: AsyncSession = Depends(get_db_session)
) -> InfrastructureHealthResponse:
    """
    Evaluates real-time utilization loads, database anomalies, and energy grid stability
    to output node health ratings, logistic failure probabilities, and remaining useful life (RUL).
    """
    result = await HealthService.get_infrastructure_diagnostics(db)
    return InfrastructureHealthResponse(
        overall_health_score=result["overall_health_score"],
        active_risks_count=result["active_risks_count"],
        reports=result["reports"]
    )


@router.get(
    "/components",
    response_model=CityHealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Compute dynamic health scores, risk levels, and confidence ratings for city infrastructure components",
)
@cache_response(ttl=CacheTTL.HEALTH.value, prefix="health")
async def get_city_infrastructure_health(
    db: AsyncSession = Depends(get_db_session)
) -> CityHealthResponse:
    """
    Evaluates real-time weather, traffic, grid energy load stability, active anomalies, 
    and social media complaint signals to compile dynamic, normalized health ratings 
    and confidence scores for each infrastructure sector.
    """
    reports = await HealthService.get_city_infrastructure_health(db)
    return CityHealthResponse(
        success=True,
        reports=reports
    )

