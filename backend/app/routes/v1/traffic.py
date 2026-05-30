from fastapi import APIRouter, Query, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import redis_client, get_db_session
from app.schemas.traffic import CurrentTrafficResponse, TrafficTrendsResponse
from app.services.traffic_service import TrafficService

router = APIRouter()


@router.get(
    "/current",
    response_model=CurrentTrafficResponse,
    status_code=status.HTTP_200_OK,
    summary="Query active road corridor flow metrics",
)
async def get_current_traffic_observations() -> CurrentTrafficResponse:
    """
    Fetch the latest road speed, travel times, jam factors, and incident counts across active corridors.
    """
    return await TrafficService.get_current_traffic(redis_client)


@router.get(
    "/trends",
    response_model=TrafficTrendsResponse,
    status_code=status.HTTP_200_OK,
    summary="Query historical road traffic trends",
)
async def get_road_corridor_trends(
    corridor: str = Query(..., description="Target corridor identifier (e.g. NYC-I95)"),
    db: AsyncSession = Depends(get_db_session),
) -> TrafficTrendsResponse:
    """
    Query chronological historical sequences (up to the last 50 poll cycles) from PostgreSQL for a specific highway corridor.
    """
    return await TrafficService.get_traffic_trends(db, corridor)
