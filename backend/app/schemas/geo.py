from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class GeoAnomalyPoint(BaseModel):
    """A geolocated anomaly event projected onto city coordinates."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    lat: float
    lng: float
    severity: str  # CRITICAL, WARNING, INFO
    category: str  # POWER, TRAFFIC, WATER, INTERNET, PUBLIC_INFRASTRUCTURE
    score: float  # Anomaly score [0.0 – 1.0]
    metric_name: str
    description: str
    timestamp: str
    district: str  # Named city zone
    acknowledged: bool = False


class GeoRegionPolygon(BaseModel):
    """GeoJSON-like polygon boundary for a city monitoring zone."""

    region_id: str
    name: str
    coordinates: List[List[float]]  # [[lat, lng], ...] closed polygon


class GeoRegionStatus(BaseModel):
    """Aggregated infrastructure health status for a named city zone."""

    model_config = ConfigDict(from_attributes=True)

    region_id: str
    name: str
    centroid_lat: float
    centroid_lng: float
    health_score: float  # [5.0 – 100.0]
    risk_level: str  # NOMINAL, LOW, MEDIUM, HIGH, CRITICAL
    anomaly_count: int
    critical_count: int
    dominant_category: Optional[str]
    polygon: List[List[float]]  # [[lat, lng], ...]


class GeoHeatmapPoint(BaseModel):
    """A single weighted point for heatmap rendering [lat, lng, intensity]."""

    lat: float
    lng: float
    intensity: float  # [0.0 – 1.0] normalized weight


class GeoMapResponse(BaseModel):
    """Complete geospatial map payload returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    anomaly_points: List[GeoAnomalyPoint]
    regions: List[GeoRegionStatus]
    heatmap_points: List[GeoHeatmapPoint]
    total_anomalies: int
    critical_count: int
    most_affected_region: Optional[str]
    last_updated: str
