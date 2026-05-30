from typing import List, Dict, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class CorrelationMatrixResponse(BaseModel):
    success: bool = Field(..., description="Successful calculation indicator")
    variables: List[str] = Field(
        ..., description="List of telemetry metric names included in matrix"
    )
    matrix: List[List[float]] = Field(
        ..., description="2D correlation coefficient grid"
    )


class GraphNode(BaseModel):
    id: str = Field(..., description="Unique node identifier")
    label: str = Field(..., description="Display label for the node")
    group: str = Field(
        ...,
        description="Telemetry source group (e.g., weather, traffic, energy, anomaly, social)",
    )


class GraphEdge(BaseModel):
    source: str = Field(..., description="Source node ID")
    target: str = Field(..., description="Target node ID")
    weight: float = Field(
        ..., description="Pearson correlation coefficient weight value"
    )


class CorrelationGraphResponse(BaseModel):
    success: bool = Field(..., description="Successful calculation indicator")
    nodes: List[GraphNode] = Field(..., description="Correlation network nodes")
    edges: List[GraphEdge] = Field(..., description="Network correlation edge weights")


class TimeOverlayResponse(BaseModel):
    success: bool = Field(..., description="Successful calculation indicator")
    timestamps: List[datetime] = Field(
        ..., description="Aligned chronological timestamps"
    )
    series: Dict[str, List[Optional[float]]] = Field(
        ..., description="Parallel aligned metric values mapping"
    )


class ActivityIntensityResponse(BaseModel):
    success: bool = Field(..., description="Successful calculation indicator")
    days: List[str] = Field(..., description="Names of DOW mapped as rows")
    hours: List[int] = Field(..., description="Hour integers mapped as columns")
    matrix: List[List[float]] = Field(
        ..., description="2D float grid of temporal activity intensity"
    )


class AnomalyConcentrationResponse(BaseModel):
    success: bool = Field(..., description="Successful calculation indicator")
    days: List[str] = Field(..., description="Names of DOW mapped as rows")
    hours: List[int] = Field(..., description="Hour integers mapped as columns")
    matrix: List[List[int]] = Field(
        ..., description="2D integer grid of anomaly counts"
    )


class SynchronizedAnomaly(BaseModel):
    id: str = Field(..., description="Unique anomaly ID.")
    timestamp: datetime = Field(
        ..., description="Timestamp of the concurrent anomaly spike."
    )
    metrics: Dict[str, float] = Field(
        ..., description="Values of active metric channels during spike."
    )
    severity: str = Field(..., description="Risk severity tier (HIGH, MEDIUM, LOW).")
    description: str = Field(..., description="Cascade failure explanation rationale.")


class SynchronizedAnomaliesResponse(BaseModel):
    success: bool = Field(True, description="Successful calculation indicator.")
    anomalies: List[SynchronizedAnomaly] = Field(
        ..., description="Synchronized anomalies failure events list."
    )


class LagCorrelation(BaseModel):
    metric_a: str = Field(..., description="Leading metric label.")
    metric_b: str = Field(..., description="Lagging metric label.")
    lag_minutes: int = Field(..., description="Lag time offset in minutes.")
    correlation: float = Field(
        ..., description="Pearson correlation score at optimal lag."
    )
    description: str = Field(
        ..., description="Explainable description of the cascade relationship."
    )


class LagAnalysisResponse(BaseModel):
    success: bool = Field(True, description="Successful calculation indicator.")
    relationships: List[LagCorrelation] = Field(
        ..., description="List of temporal lag cascade relationships."
    )
