from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class ForecastRecord(BaseModel):
    timestamp: datetime = Field(
        ..., description="Timestamp for actual or forecasted telemetry cell"
    )
    actual: Optional[float] = Field(
        None, description="Actual observed metric value (null during forecast horizon)"
    )
    forecast: float = Field(..., description="Projected mean metric value")
    upper_bound: float = Field(
        ..., description="95% confidence upper bound forecast limit"
    )
    lower_bound: float = Field(
        ..., description="95% confidence lower bound forecast limit"
    )
    is_forecast: bool = Field(
        ...,
        description="True if inside predicted future range, False if historical actual",
    )


class PredictedAnomaly(BaseModel):
    timestamp: datetime = Field(
        ..., description="Timestamp when predicted future anomaly starts"
    )
    predicted_value: float = Field(
        ..., description="Peak forecasted anomaly score or load level"
    )
    severity: str = Field(..., description="Severity grading (WARNING or CRITICAL)")
    description: str = Field(
        ..., description="Explainable description of predicted threat event"
    )


class ExplainableForecasting(BaseModel):
    trend_direction: str = Field(
        ..., description="Overall trend vector (UPWARD_TREND, DOWNWARD_TREND, STABLE)"
    )
    trend_summary: str = Field(
        ..., description="Paragraph detailing mathematical trend findings"
    )
    peak_day_of_week: str = Field(
        ..., description="Projected peak usage day of the week based on history"
    )
    peak_hour_of_day: int = Field(
        ..., description="Projected peak hour of day utilization window (0-23)"
    )
    analysis_notes: List[str] = Field(
        ..., description="Text summaries explaining seasonal daily/weekly findings"
    )


class ForecastResponse(BaseModel):
    success: bool = Field(..., description="Calculated successfully or failed flag")
    metric_name: str = Field(
        ..., description="Human-readable label of the forecasted telemetry metric"
    )
    records: List[ForecastRecord] = Field(
        ..., description="Aligned timeline records of history + predictions"
    )
    predicted_anomalies: List[PredictedAnomaly] = Field(
        ..., description="List of forecasted future anomalies"
    )
    explanation: ExplainableForecasting = Field(
        ..., description="Human-explainable seasonality insights"
    )
