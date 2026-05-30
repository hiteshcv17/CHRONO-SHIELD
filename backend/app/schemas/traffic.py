from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class TrafficRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    timestamp: datetime = Field(
        ..., description="Timestamp of the traffic observations"
    )
    corridor_id: str = Field(
        ..., description="Highway corridor identifier (e.g. NYC-I95)"
    )
    bbox: Optional[str] = Field(None, description="Geographic boundary coordinates")
    flow_speed_kmh: Optional[float] = Field(
        None, description="Current speed of traffic flow in km/h"
    )
    free_flow_speed_kmh: Optional[float] = Field(
        None, description="Free flow reference speed of road in km/h"
    )
    jam_factor: Optional[float] = Field(
        None, description="Scale rating from 0.0 (open) to 10.0 (gridlock)"
    )
    congestion_level: Optional[str] = Field(
        None,
        description="Functional road congestion index (SAFE, SLOW, CONGESTED, GRIDLOCK)",
    )
    incident_count: Optional[int] = Field(
        None, description="Number of current reported incidents in boundary"
    )
    travel_time_seconds: Optional[int] = Field(
        None, description="Average estimated corridor transit travel time in seconds"
    )
    confidence_score: Optional[float] = Field(
        None, description="HERE/TomTom telemetry coordinate mapping confidence rating"
    )


class CurrentTrafficResponse(BaseModel):
    success: bool = Field(..., description="Indicator of a successful data pull")
    fetched_at: datetime = Field(..., description="Timestamp when data was synced")
    records: List[TrafficRecord] = Field(
        default_factory=list, description="Latest corridor flow metrics"
    )


class TrafficTrendsResponse(BaseModel):
    corridor: str = Field(..., description="Monitored road corridor ID")
    records: List[TrafficRecord] = Field(
        default_factory=list, description="Historical sequence data for charting"
    )
