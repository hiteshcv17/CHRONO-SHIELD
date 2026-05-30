from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db_session
from app.schemas.geo import GeoAnomalyPoint, GeoRegionStatus, GeoHeatmapPoint, GeoMapResponse
from app.services.geo_service import GeoService

from app.core.auth import get_current_user

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("/map", response_model=GeoMapResponse, status_code=status.HTTP_200_OK)
async def get_geo_map(
    db: AsyncSession = Depends(get_db_session)
):
    """
    Returns the complete geospatial map payload:
    - Geolocated anomaly markers with severity, category, and description
    - Heatmap intensity grid points for visual density rendering
    - Per-zone regional health scores and polygon boundaries
    """
    data = await GeoService.get_full_map(db)
    return data


@router.get("/regions", response_model=List[GeoRegionStatus], status_code=status.HTTP_200_OK)
async def get_geo_regions(
    db: AsyncSession = Depends(get_db_session)
):
    """
    Returns infrastructure health aggregates per monitoring zone.
    Includes polygon boundaries for map rendering, health scores, risk levels,
    anomaly counts, and dominant infrastructure category.
    """
    return await GeoService.get_region_statuses(db)


@router.get("/anomaly-points", response_model=List[GeoAnomalyPoint], status_code=status.HTTP_200_OK)
async def get_geo_anomaly_points(
    severity: Optional[str] = Query(None, description="Filter by severity: CRITICAL, WARNING, INFO"),
    category: Optional[str] = Query(None, description="Filter by infrastructure category: POWER, TRAFFIC, WATER, INTERNET, PUBLIC_INFRASTRUCTURE"),
    district: Optional[str] = Query(None, description="Filter by named city zone"),
    limit: int = Query(200, ge=1, le=1000, description="Max anomaly points to return"),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Returns geolocated anomaly points with optional severity, category, and district filters.
    Suitable for incremental map updates or filtered heatmap rendering.
    """
    points = await GeoService.get_anomaly_points(db)
    
    # Apply optional filters
    if severity:
        points = [p for p in points if p["severity"].upper() == severity.upper()]
    if category:
        points = [p for p in points if p["category"].upper() == category.upper()]
    if district:
        points = [p for p in points if district.lower() in p["district"].lower()]
    
    return points[:limit]


@router.get("/heatmap", response_model=List[GeoHeatmapPoint], status_code=status.HTTP_200_OK)
async def get_geo_heatmap(
    db: AsyncSession = Depends(get_db_session)
):
    """
    Returns weighted heatmap grid points for Leaflet.heat rendering.
    Intensity is normalized [0.0 – 1.0], higher values indicate denser anomaly clustering.
    """
    return await GeoService.get_heatmap_points(db)
