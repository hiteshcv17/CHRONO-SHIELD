from fastapi import APIRouter, Query, status, BackgroundTasks, Depends
from typing import List
from pydantic import BaseModel

from app.schemas.benchmark import BenchmarkRun, BenchmarkRequest
from app.services.benchmark_service import BenchmarkService

from app.core.auth import require_admin

router = APIRouter(dependencies=[Depends(require_admin)])


@router.post("/run", response_model=BenchmarkRun, status_code=status.HTTP_200_OK)
async def run_benchmark(req: BenchmarkRequest):
    """
    Run the full forecasting benchmark: Prophet vs ARIMA vs ETS.
    Evaluates on MAE, RMSE, MAPE, R², training time, and inference time
    across all requested infrastructure metric types.

    ⚠ This endpoint runs actual model training — expect 10–60s response time.
    """
    return BenchmarkService.run_benchmark(
        metric_types=req.metric_types,
        horizon_steps=req.horizon_steps,
        n_samples=req.n_samples,
        include_ets=req.include_ets,
    )


@router.get("/quick", response_model=BenchmarkRun, status_code=status.HTTP_200_OK)
async def run_quick_benchmark(
    metric_type: str = Query(
        "power", description="Single metric type to benchmark quickly"
    ),
    n_samples: int = Query(120, ge=60, le=500),
    horizon: int = Query(12, ge=4, le=48),
):
    """
    Quick single-dataset benchmark for low-latency API testing.
    """
    return BenchmarkService.run_benchmark(
        metric_types=[metric_type],
        horizon_steps=horizon,
        n_samples=n_samples,
        include_ets=True,
    )


@router.get("/preview/{metric_type}", status_code=status.HTTP_200_OK)
async def get_dataset_preview(
    metric_type: str,
    n_samples: int = Query(200, ge=48, le=720),
):
    """
    Return the raw synthetic time-series values and statistics for a
    given metric type — useful for dataset visualisation in the frontend.
    """
    return BenchmarkService.get_dataset_preview(metric_type, n_samples)
