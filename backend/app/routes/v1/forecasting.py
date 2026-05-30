from fastapi import APIRouter, Query, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db_session
from app.schemas.forecasting import ForecastResponse
from app.services.forecasting_service import ForecastingService
from app.utils.cache import cache_response
from app.utils.constants import CacheTTL

from app.core.auth import require_analyst

router = APIRouter(dependencies=[Depends(require_analyst)])


@router.get(
    "/predict",
    response_model=ForecastResponse,
    status_code=status.HTTP_200_OK,
    summary="Compute neural sequence telemetry forecasting via Prophet",
)
@cache_response(ttl=CacheTTL.FORECASTING.value, prefix="forecast")
async def predict_telemetry(
    metric_id: str = Query(
        "energy_demand", description="Internal ID of metric to predict"
    ),
    horizon_hours: int = Query(
        24, description="Forecast timeline horizon (e.g., 24, 168, 720)"
    ),
    city: str = Query(
        "New York", description="Target location for time-series extraction"
    ),
    db: AsyncSession = Depends(get_db_session),
) -> ForecastResponse:
    """
    Fits Prophet time-series models on aligned historical data, predicting future
    expected pathways, 95% confidence bands, future anomaly threat points,
    and returns human-explainable seasonal insights.
    """
    result = await ForecastingService.get_telemetry_forecast(
        db=db, metric_id=metric_id, horizon_hours=horizon_hours, city=city
    )
    return ForecastResponse(
        success=True,
        metric_name=result["metric_name"],
        records=result["records"],
        predicted_anomalies=result["predicted_anomalies"],
        explanation=result["explanation"],
    )
