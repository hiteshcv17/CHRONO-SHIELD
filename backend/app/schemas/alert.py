from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class AlertStatusUpdate(BaseModel):
    acknowledged: Optional[bool] = Field(None, description="Mark alert as acknowledged")
    resolved: Optional[bool] = Field(None, description="Mark alert as resolved")


class PrioritizedAlertResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="Unique alert ID Designation")
    anomaly_id: str = Field(..., description="Original triggering anomaly record ID")
    metric_name: str = Field(
        ..., description="Target metric channel source designation"
    )
    original_severity: str = Field(..., description="Standard anomaly severity level")
    current_severity: str = Field(
        ..., description="Dynamic current escalated severity level"
    )
    priority_score: float = Field(
        ..., description="Aggregated priority rating [0.0 - 100.0]"
    )
    status: str = Field(
        ...,
        description="Operational alert status (ACTIVE, ACKNOWLEDGED, SUPPRESSED, ESCALATED, RESOLVED)",
    )
    occurrence_count: int = Field(..., description="De-duplication count index")
    timestamp: datetime = Field(..., description="Initial incident creation time")
    last_occurrence: datetime = Field(
        ..., description="Last merged duplicate occurrence time"
    )
    cooldown_until: Optional[datetime] = Field(
        None, description="Active cooldown limit time"
    )
    escalation_level: int = Field(
        ..., description="Current unacknowledged SLA escalation breach tier"
    )
    description: str = Field(..., description="Explainable diagnostic explanation")
