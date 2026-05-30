from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator


class AnomalyBase(BaseModel):
    metric_name: str = Field(
        ..., max_length=100, description="Metric target name (e.g. CPU_Usage)"
    )
    severity: str = Field(
        ..., description="Alert classification level (CRITICAL, WARNING, INFO)"
    )
    score: float = Field(
        ..., ge=0.0, le=1.0, description="ML anomaly score rating [0.0 - 1.0]"
    )
    description: str = Field(
        ..., max_length=500, description="Detailed explanation of anomalous signature"
    )

    @field_validator("description", "metric_name")
    @classmethod
    def sanitize_fields(cls, v: str) -> str:
        from app.utils.security import sanitize_text

        return sanitize_text(v)

    @field_validator("severity")
    @classmethod
    def validate_severity_levels(cls, v: str) -> str:
        upper_v = v.upper()
        allowed = {"CRITICAL", "WARNING", "INFO"}
        if upper_v not in allowed:
            raise ValueError(f"Severity must match standard levels: {allowed}")
        return upper_v


class AnomalyCreate(AnomalyBase):
    id: str = Field(..., description="Unique event identifier (e.g. anm-092)")
    timestamp: datetime = Field(
        ..., description="Datetime corresponding to anomaly discovery"
    )


class AnomalyUpdate(BaseModel):
    acknowledged: bool = Field(..., description="Acknowledge alert flag")


class AnomalyResponse(AnomalyBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    timestamp: datetime
    acknowledged: bool
