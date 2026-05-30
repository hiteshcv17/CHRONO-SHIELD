"""
Phase 27 — Historical Replay & Incident Timeline Analysis
Pydantic schemas for the forensic replay engine.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel


class SeverityDistribution(BaseModel):
    CRITICAL: int = 0
    WARNING: int = 0
    INFO: int = 0


class CategoryDistribution(BaseModel):
    POWER: int = 0
    TRAFFIC: int = 0
    WATER: int = 0
    INTERNET: int = 0
    PUBLIC_INFRASTRUCTURE: int = 0


class TimelineBucket(BaseModel):
    """
    A single 30-minute time window in the incident timeline.
    Aggregates all anomaly events that occurred within this window.
    """

    bucket_index: int
    timestamp_start: str
    timestamp_end: str
    label: str  # Human-readable e.g. "May 28, 02:00 – 02:30"
    anomaly_count: int
    critical_count: int
    severity_distribution: SeverityDistribution
    category_distribution: CategoryDistribution
    peak_score: float  # Highest anomaly score in this bucket [0–1]
    health_delta: float  # Change in system health during this window
    event_ids: List[str]  # IDs of incidents in this bucket


class IncidentRecord(BaseModel):
    """
    A single reconstructed incident record for forensic analysis and comparison.
    """

    id: str
    timestamp: str
    metric_name: str
    severity: str
    category: str
    score: float
    description: str
    district: str
    acknowledged: bool
    duration_minutes: int  # Estimated incident duration
    cascaded: bool  # Whether this triggered downstream events
    related_ids: List[str]  # IDs of correlated incidents
    root_cause_hint: Optional[str]  # NLP-derived probable root cause
    resolution_hint: Optional[str]  # Suggested remediation step
    bucket_index: int  # Which timeline bucket this belongs to


class ReplayFrame(BaseModel):
    """
    A single playback frame — snapshot of system state at a specific bucket.
    """

    bucket: TimelineBucket
    active_incidents: List[IncidentRecord]
    cumulative_critical: int
    cumulative_total: int
    system_health: float  # Estimated overall health [0–100] at this moment
    dominant_category: Optional[str]
    alert_level: str  # NOMINAL / ELEVATED / HIGH / CRISIS


class ReplayTimelineResponse(BaseModel):
    """
    Full timeline payload returned for replay initialization.
    """

    buckets: List[TimelineBucket]
    incidents: List[IncidentRecord]
    time_range_hours: int
    bucket_duration_minutes: int
    total_incidents: int
    total_critical: int
    peak_bucket_index: int  # Bucket with most activity
    timeline_start: str
    timeline_end: str


class IncidentComparisonResponse(BaseModel):
    """
    Side-by-side comparison of two incidents for forensic analysis.
    """

    incident_a: IncidentRecord
    incident_b: IncidentRecord
    similarity_score: float  # 0–1, how similar these incidents are
    shared_categories: List[str]
    shared_districts: List[str]
    time_delta_minutes: int  # Time between the two incidents
    likely_correlated: bool
    severity_diff: str  # Which is worse and by how much
    score_diff: float
    combined_risk: str  # Overall risk of both occurring together
