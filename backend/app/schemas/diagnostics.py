from typing import Dict, Any, List
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = Field(..., description="System gateway state (e.g. healthy)")
    service: str = Field(..., description="Service identifier label")
    environment: str = Field(..., description="Target runtime container environment")


class DependencyStatus(BaseModel):
    name: str = Field(..., description="Name of the service dependency")
    connected: bool = Field(..., description="Connectivity confirmation flag")
    latency_ms: float = Field(..., description="Ping latency timing")


class StatusResponse(BaseModel):
    status: str = Field(..., description="Aggregated systems diagnostic rating")
    dependencies: List[DependencyStatus] = Field(..., description="Statuses of database and cache streams")
    system_metrics: Dict[str, Any] = Field(..., description="Memory utilization and gateway load indicators")


class VersionResponse(BaseModel):
    service: str = Field(..., description="Service identifier label")
    version: str = Field(..., description="Current release version string")
    api_v1_prefix: str = Field(..., description="Active API version route string")
