from fastapi import APIRouter, Body, Query, status
from typing import List, Optional
from pydantic import BaseModel

from app.schemas.explain import AnomalyExplanation, ExplainBatchResponse
from app.services.explain_service import ExplainService

from fastapi import Depends
from app.core.auth import require_analyst
from app.utils.cache import cache_response
from app.utils.constants import CacheTTL


router = APIRouter(dependencies=[Depends(require_analyst)])


class AnomalyExplainRequest(BaseModel):
    anomaly_id: str
    metric_name: str
    severity: str
    category: str
    score: float
    timestamp: str
    district: str
    description: str = ""
    related_ids: List[str] = []


class BatchExplainRequest(BaseModel):
    anomalies: List[AnomalyExplainRequest]


@router.post(
    "/anomaly", response_model=AnomalyExplanation, status_code=status.HTTP_200_OK
)
@cache_response(ttl=CacheTTL.EXPLAIN.value, prefix="explain")
async def explain_anomaly(req: AnomalyExplainRequest):
    """
    Generate a full XAI explanation for a single anomaly event.
    Returns contributing factors, correlation chain, chain-of-thought reasoning,
    and natural language narrative.
    """
    return ExplainService.explain_anomaly(
        anomaly_id=req.anomaly_id,
        metric_name=req.metric_name,
        severity=req.severity,
        category=req.category,
        score=req.score,
        timestamp=req.timestamp,
        district=req.district,
        description=req.description,
        related_ids=req.related_ids,
    )


@router.post(
    "/batch", response_model=ExplainBatchResponse, status_code=status.HTTP_200_OK
)
@cache_response(ttl=CacheTTL.EXPLAIN.value, prefix="explain")
async def explain_batch(req: BatchExplainRequest):
    """
    Generate XAI explanations for multiple anomalies simultaneously.
    Includes cross-incident pattern analysis and system-level narrative.
    """
    return ExplainService.explain_batch([a.model_dump() for a in req.anomalies])


@router.get(
    "/preview", response_model=AnomalyExplanation, status_code=status.HTTP_200_OK
)
@cache_response(ttl=CacheTTL.EXPLAIN.value, prefix="explain")
async def explain_preview(
    metric: str = Query("power_outage", description="Metric name to preview"),
    severity: str = Query("CRITICAL", description="CRITICAL | WARNING | INFO"),
    category: str = Query("POWER"),
    score: float = Query(0.93, ge=0.0, le=1.0),
    district: str = Query("East Industrial"),
):
    """
    Preview endpoint — generates a demo explanation without requiring a request body.
    Useful for frontend development and testing.
    """
    from datetime import datetime

    return ExplainService.explain_anomaly(
        anomaly_id="PREVIEW-001",
        metric_name=metric,
        severity=severity,
        category=category,
        score=score,
        timestamp=datetime.utcnow().isoformat(),
        district=district,
    )
