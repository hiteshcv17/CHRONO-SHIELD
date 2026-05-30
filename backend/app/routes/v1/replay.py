from fastapi import APIRouter, Query, status
from app.schemas.replay import (
    ReplayTimelineResponse,
    IncidentComparisonResponse,
    ReplayFrame,
)
from app.services.replay_service import ReplayService

from fastapi import Depends
from app.core.auth import require_analyst

router = APIRouter(dependencies=[Depends(require_analyst)])


@router.get("/timeline", response_model=ReplayTimelineResponse, status_code=status.HTTP_200_OK)
async def get_replay_timeline(
    hours: int = Query(24, ge=1, le=168, description="Time range in hours (1–168 / up to 7 days)"),
):
    """
    Returns the full replay timeline payload:
    - 30-minute buckets with event density, severity, and health metrics
    - Full incident corpus for forensic analysis
    - Peak bucket index and aggregate statistics
    """
    return ReplayService.get_timeline(time_range_hours=hours)


@router.get("/frame/{bucket_index}", response_model=ReplayFrame, status_code=status.HTTP_200_OK)
async def get_replay_frame(
    bucket_index: int,
    hours: int = Query(24, ge=1, le=168),
):
    """
    Returns the system state snapshot at a specific timeline bucket.
    Includes active incidents, cumulative counters, and computed health/alert level.
    """
    data = ReplayService.get_timeline(time_range_hours=hours)
    return ReplayService.get_replay_frame(bucket_index, data["incidents"])


@router.get("/compare", response_model=IncidentComparisonResponse, status_code=status.HTTP_200_OK)
async def compare_incidents(
    id_a: str = Query(..., description="First incident ID (e.g. INC-005)"),
    id_b: str = Query(..., description="Second incident ID (e.g. INC-006)"),
    hours: int = Query(24, ge=1, le=168),
):
    """
    Forensic comparison of two incident records.
    Returns similarity score, shared attributes, time delta, and combined risk assessment.
    """
    data = ReplayService.get_timeline(time_range_hours=hours)
    result = ReplayService.compare_incidents(id_a, id_b, data["incidents"])
    if not result:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"One or both incident IDs not found: {id_a}, {id_b}")
    return result
