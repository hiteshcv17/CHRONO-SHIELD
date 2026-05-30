from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, ConfigDict, Field


class ReportSummaryMetrics(BaseModel):
    total_anomalies: int = Field(
        ..., description="Total anomalies identified during period"
    )
    critical_count: int = Field(..., description="Critical severity anomaly counts")
    warning_count: int = Field(..., description="Warning severity anomaly counts")
    info_count: int = Field(..., description="Info severity anomaly counts")
    peak_score: float = Field(..., description="Maximum reconstruction loss score")
    total_alerts: int = Field(..., description="Total generated prioritized alerts")
    resolved_alerts: int = Field(
        ..., description="Acknowledged or resolved alerts count"
    )
    sla_violations: int = Field(..., description="Breached SLA response counts")
    system_health_avg: float = Field(
        ..., description="Average infrastructure health score [0-100]"
    )
    lowest_health_sector: Optional[str] = Field(
        None, description="Poorest performing infrastructure sector"
    )
    lowest_health_score: Optional[float] = Field(
        None, description="Lowest sector health value"
    )
    forecast_mae: Optional[float] = Field(
        None, description="Average forecast mean absolute error"
    )
    forecast_rmse: Optional[float] = Field(
        None, description="Average forecast root mean squared error"
    )
    forecast_trend: Optional[str] = Field(
        None,
        description="Predicted trend direction (STABLE, INCREASING_RISK, DECREASING_RISK)",
    )


class ReportCreate(BaseModel):
    report_type: Literal["DAILY", "WEEKLY"] = Field(
        ..., description="Type of reporting cycle"
    )
    start_date: datetime = Field(..., description="Starting boundary datetime")
    end_date: datetime = Field(..., description="Ending boundary datetime")


class ReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    report_type: Literal["DAILY", "WEEKLY"]
    start_date: datetime
    end_date: datetime
    status: Literal["GENERATING", "READY", "FAILED"]
    summary: Optional[str] = Field(None, description="JSON encoded summary metrics")
    pdf_path: Optional[str] = None
    csv_path: Optional[str] = None
    created_at: datetime
