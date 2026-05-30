from typing import List, Dict, Any
from pydantic import BaseModel, Field


class NodeHealthReport(BaseModel):
    name: str = Field(
        ..., description="Unique hostname designation of the cluster node"
    )
    node_type: str = Field(
        ...,
        description="Infrastructure role classification (e.g. API Gateway, Database)",
    )
    uptime: str = Field(..., description="Chronological runtime signature of node")
    cpu_load: int = Field(..., description="Current live CPU load rate (%)")
    memory_saturation: int = Field(
        ..., description="Current live Memory saturation level (%)"
    )
    health_score: int = Field(
        ..., description="Aggregated mathematical health score (0-100)"
    )
    failure_probability: float = Field(
        ..., description="Projected probability of failure inside next 30 days (%)"
    )
    remaining_useful_life_days: int = Field(
        ...,
        description="Estimated remaining useful life (RUL) in days before threshold collapse",
    )
    risk_tier: str = Field(
        ..., description="Risk urgency assessment (NOMINAL, MEDIUM, HIGH, CRITICAL)"
    )
    explanation: str = Field(
        ...,
        description="Explainable diagnostic summary detailing systemic anomalies or violations",
    )


class InfrastructureHealthResponse(BaseModel):
    overall_health_score: int = Field(
        ...,
        description="Aggregated average health score across entire active cluster pool",
    )
    active_risks_count: int = Field(
        ...,
        description="Count of nodes currently flagging at High or Critical failure risks",
    )
    reports: List[NodeHealthReport] = Field(
        ..., description="List of predictive health diagnostics per cluster node"
    )


class ComponentHealthReport(BaseModel):
    category: str = Field(
        ..., description="Infrastructure component category name (e.g. POWER, TRAFFIC)"
    )
    health_score: int = Field(
        ..., description="Normalized health score between 0 and 100"
    )
    risk_level: str = Field(
        ..., description="Risk tier assessment (NOMINAL, LOW, MEDIUM, HIGH, CRITICAL)"
    )
    confidence_score: int = Field(
        ...,
        description="Mathematical confidence score (0-100%) based on sensor source density",
    )
    metrics: Dict[str, Any] = Field(
        ..., description="Live physical telemetry metrics mapped in this sector"
    )
    penalties_breakdown: Dict[str, float] = Field(
        ...,
        description="Breakdown of calculated anomaly, social, and telemetry penalties",
    )
    explanation: str = Field(
        ..., description="Explainable AI diagnostic rationale detailing active alerts"
    )


class CityHealthResponse(BaseModel):
    success: bool = Field(True, description="Successful calculation indicator")
    reports: List[ComponentHealthReport] = Field(
        ...,
        description="Dynamic health score assessment reports for all infrastructure sectors",
    )
