from fastapi import APIRouter, Query, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import redis_client, get_db_session
from app.schemas.weather import CurrentWeatherResponse, WeatherTrendsResponse
from app.services.weather_service import WeatherService

from app.core.auth import get_current_user

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get(
    "/current",
    response_model=CurrentWeatherResponse,
    status_code=status.HTTP_200_OK,
    summary="Query current environmental observations",
)
async def get_current_observations() -> CurrentWeatherResponse:
    """
    Fetch the latest atmospheric weather telemetry metrics for New York, London, and Singapore.
    """
    return await WeatherService.get_current_weather(redis_client)


@router.get(
    "/trends",
    response_model=WeatherTrendsResponse,
    status_code=status.HTTP_200_OK,
    summary="Query weather parameter historical trends",
)
async def get_weather_parameter_trends(
    city: str = Query(..., description="Target location city name (e.g. London)"),
    db: AsyncSession = Depends(get_db_session),
) -> WeatherTrendsResponse:
    """
    Query chronological historical sequences (up to the last 50 poll cycles) from PostgreSQL for a specific city.
    """
    return await WeatherService.get_weather_trends(db, city)
