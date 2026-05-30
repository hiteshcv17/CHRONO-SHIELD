import logging
import math
import random
import hashlib
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("geo_service")


# ==============================================================================
# City Zone Definitions — 5 Urban Monitoring Districts (Delhi NCR-like grid)
# ==============================================================================
CITY_ZONES = [
    {
        "region_id": "north_district",
        "name": "North District",
        "centroid": (28.7041, 77.1025),
        "polygon": [
            [28.750, 77.050],
            [28.750, 77.160],
            [28.680, 77.160],
            [28.680, 77.050],
            [28.750, 77.050],
        ],
        "primary_categories": ["POWER", "INTERNET"],
    },
    {
        "region_id": "central_grid",
        "name": "Central Grid",
        "centroid": (28.6304, 77.2177),
        "polygon": [
            [28.670, 77.180],
            [28.670, 77.270],
            [28.590, 77.270],
            [28.590, 77.180],
            [28.670, 77.180],
        ],
        "primary_categories": ["PUBLIC_INFRASTRUCTURE", "WATER"],
    },
    {
        "region_id": "south_harbor",
        "name": "South Harbor",
        "centroid": (28.5355, 77.3910),
        "polygon": [
            [28.580, 77.350],
            [28.580, 77.430],
            [28.490, 77.430],
            [28.490, 77.350],
            [28.580, 77.350],
        ],
        "primary_categories": ["WATER", "PUBLIC_INFRASTRUCTURE"],
    },
    {
        "region_id": "east_industrial",
        "name": "East Industrial",
        "centroid": (28.6280, 77.3781),
        "polygon": [
            [28.680, 77.340],
            [28.680, 77.420],
            [28.575, 77.420],
            [28.575, 77.340],
            [28.680, 77.340],
        ],
        "primary_categories": ["TRAFFIC", "POWER"],
    },
    {
        "region_id": "west_residential",
        "name": "West Residential",
        "centroid": (28.6519, 77.0690),
        "polygon": [
            [28.710, 77.030],
            [28.710, 77.110],
            [28.590, 77.110],
            [28.590, 77.030],
            [28.710, 77.030],
        ],
        "primary_categories": ["INTERNET", "TRAFFIC"],
    },
]

# Category → preferred zone mapping
CATEGORY_ZONE_MAP: Dict[str, str] = {
    "POWER": "north_district",
    "INTERNET": "north_district",
    "WATER": "south_harbor",
    "PUBLIC_INFRASTRUCTURE": "central_grid",
    "TRAFFIC": "east_industrial",
}

# Category → inferred from metric name keywords
METRIC_CATEGORY_MAP: Dict[str, str] = {
    "energy": "POWER",
    "power": "POWER",
    "grid": "POWER",
    "voltage": "POWER",
    "cpu": "INTERNET",
    "memory": "INTERNET",
    "network": "INTERNET",
    "internet": "INTERNET",
    "traffic": "TRAFFIC",
    "jam": "TRAFFIC",
    "vehicle": "TRAFFIC",
    "water": "WATER",
    "pipe": "WATER",
    "flood": "WATER",
    "infrastructure": "PUBLIC_INFRASTRUCTURE",
    "road": "PUBLIC_INFRASTRUCTURE",
    "signal": "PUBLIC_INFRASTRUCTURE",
}


def _infer_category(metric_name: str) -> str:
    """Infer infrastructure category from metric name keywords."""
    lower = metric_name.lower()
    for keyword, cat in METRIC_CATEGORY_MAP.items():
        if keyword in lower:
            return cat
    return "PUBLIC_INFRASTRUCTURE"


def _get_zone(region_id: str) -> Dict:
    """Return zone config by ID."""
    return next((z for z in CITY_ZONES if z["region_id"] == region_id), CITY_ZONES[2])


def _jitter_coords(
    base_lat: float, base_lng: float, seed: str, scale: float = 0.018
) -> Tuple[float, float]:
    """Deterministically scatter points within a zone based on a hash seed."""
    h = int(hashlib.md5(seed.encode()).hexdigest(), 16)
    lat_offset = ((h % 1000) / 1000.0 - 0.5) * scale
    lng_offset = (((h // 1000) % 1000) / 1000.0 - 0.5) * scale
    return (round(base_lat + lat_offset, 6), round(base_lng + lng_offset, 6))


def _severity_weight(severity: str) -> float:
    """Convert severity string to numeric intensity weight."""
    return {"CRITICAL": 1.0, "WARNING": 0.6, "INFO": 0.25}.get(severity.upper(), 0.3)


def _health_from_anomalies(anomalies_in_zone: List[Dict]) -> Tuple[float, str]:
    """
    Compute zone health score [5–100] and risk level from a list of anomaly records in that zone.
    """
    if not anomalies_in_zone:
        return 85.0, "NOMINAL"

    penalty = sum(
        _severity_weight(a.get("severity", "INFO")) * 18.0 * a.get("score", 0.5)
        for a in anomalies_in_zone
    )
    score = max(5.0, min(100.0, 92.0 - penalty))

    if score >= 80:
        risk = "NOMINAL"
    elif score >= 65:
        risk = "LOW"
    elif score >= 45:
        risk = "MEDIUM"
    elif score >= 25:
        risk = "HIGH"
    else:
        risk = "CRITICAL"

    return round(score, 1), risk


class GeoService:
    """
    Geospatial projection and region aggregation engine for ChronoShield AI.

    Projects infrastructure telemetry and anomaly events onto geolocated city
    coordinates, enabling interactive map visualization with heatmap overlays
    and region-based health monitoring.
    """

    # ── Fallback Anomaly Dataset (used when DB unavailable) ─────────────────
    _MOCK_ANOMALIES = [
        {
            "id": "geo-001",
            "metric_name": "energy_demand",
            "severity": "CRITICAL",
            "score": 0.91,
            "description": "Grid instability detected — peak demand spike",
            "timestamp": "2026-05-28T12:01:00",
            "acknowledged": False,
        },
        {
            "id": "geo-002",
            "metric_name": "traffic_jam",
            "severity": "WARNING",
            "score": 0.72,
            "description": "Severe congestion — East Industrial corridor",
            "timestamp": "2026-05-28T12:04:00",
            "acknowledged": False,
        },
        {
            "id": "geo-003",
            "metric_name": "water_pressure",
            "severity": "CRITICAL",
            "score": 0.88,
            "description": "Low pressure anomaly — South Harbor pipeline",
            "timestamp": "2026-05-28T12:07:00",
            "acknowledged": False,
        },
        {
            "id": "geo-004",
            "metric_name": "network_latency",
            "severity": "WARNING",
            "score": 0.65,
            "description": "Elevated latency — North District CDN node",
            "timestamp": "2026-05-28T12:09:00",
            "acknowledged": True,
        },
        {
            "id": "geo-005",
            "metric_name": "cpu_usage",
            "severity": "INFO",
            "score": 0.45,
            "description": "High CPU utilization — API Gateway cluster",
            "timestamp": "2026-05-28T12:12:00",
            "acknowledged": False,
        },
        {
            "id": "geo-006",
            "metric_name": "road_signal",
            "severity": "WARNING",
            "score": 0.58,
            "description": "Signal failure — Central Grid intersection",
            "timestamp": "2026-05-28T12:15:00",
            "acknowledged": False,
        },
        {
            "id": "geo-007",
            "metric_name": "grid_voltage",
            "severity": "CRITICAL",
            "score": 0.95,
            "description": "Critical voltage drop — West Residential zone",
            "timestamp": "2026-05-28T12:18:00",
            "acknowledged": False,
        },
        {
            "id": "geo-008",
            "metric_name": "flood_sensor",
            "severity": "WARNING",
            "score": 0.70,
            "description": "Rainfall accumulation — South Harbor basin",
            "timestamp": "2026-05-28T12:21:00",
            "acknowledged": False,
        },
        {
            "id": "geo-009",
            "metric_name": "vehicle_count",
            "severity": "INFO",
            "score": 0.38,
            "description": "Unusual vehicle density — East Industrial",
            "timestamp": "2026-05-28T12:24:00",
            "acknowledged": True,
        },
        {
            "id": "geo-010",
            "metric_name": "internet_bandwidth",
            "severity": "CRITICAL",
            "score": 0.82,
            "description": "Bandwidth saturation — North District backbone",
            "timestamp": "2026-05-28T12:27:00",
            "acknowledged": False,
        },
        {
            "id": "geo-011",
            "metric_name": "water_quality",
            "severity": "WARNING",
            "score": 0.60,
            "description": "Turbidity spike — Central water treatment",
            "timestamp": "2026-05-28T12:30:00",
            "acknowledged": False,
        },
        {
            "id": "geo-012",
            "metric_name": "power_outage",
            "severity": "CRITICAL",
            "score": 0.98,
            "description": "Complete power outage — East Industrial block",
            "timestamp": "2026-05-28T12:33:00",
            "acknowledged": False,
        },
        {
            "id": "geo-013",
            "metric_name": "traffic_accident",
            "severity": "WARNING",
            "score": 0.67,
            "description": "Multi-vehicle incident — North District highway",
            "timestamp": "2026-05-28T12:36:00",
            "acknowledged": False,
        },
        {
            "id": "geo-014",
            "metric_name": "infrastructure_defect",
            "severity": "INFO",
            "score": 0.42,
            "description": "Pothole report cluster — West Residential",
            "timestamp": "2026-05-28T12:39:00",
            "acknowledged": True,
        },
        {
            "id": "geo-015",
            "metric_name": "network_packet_loss",
            "severity": "WARNING",
            "score": 0.73,
            "description": "Packet loss spike — Central Grid fiber link",
            "timestamp": "2026-05-28T12:42:00",
            "acknowledged": False,
        },
    ]

    @staticmethod
    async def get_anomaly_points(
        db: Optional[AsyncSession] = None,
    ) -> List[Dict[str, Any]]:
        """
        Build geolocated anomaly points by projecting anomaly records onto city coordinates.
        Attempts to read from DB; falls back to mock dataset if DB unavailable.
        """
        raw_anomalies = []

        if db is not None:
            try:
                from app.services.anomaly_service import AnomalyService

                records = await AnomalyService.query_anomalies(db, limit=100)
                raw_anomalies = [
                    {
                        "id": r.id,
                        "metric_name": r.metric_name,
                        "severity": r.severity,
                        "score": float(r.score),
                        "description": r.description,
                        "timestamp": str(r.timestamp),
                        "acknowledged": bool(r.acknowledged),
                    }
                    for r in records
                ]
            except Exception as e:
                logger.warning(
                    f"DB anomaly query failed for geo projection: {e}. Using mock data."
                )

        if not raw_anomalies:
            raw_anomalies = GeoService._MOCK_ANOMALIES.copy()

        # Project each anomaly onto city coordinates
        result = []
        for anomaly in raw_anomalies:
            category = _infer_category(anomaly["metric_name"])
            zone_id = CATEGORY_ZONE_MAP.get(category, "central_grid")
            zone = _get_zone(zone_id)
            base_lat, base_lng = zone["centroid"]
            lat, lng = _jitter_coords(base_lat, base_lng, anomaly["id"])

            result.append(
                {
                    "id": anomaly["id"],
                    "lat": lat,
                    "lng": lng,
                    "severity": anomaly["severity"],
                    "category": category,
                    "score": anomaly["score"],
                    "metric_name": anomaly["metric_name"],
                    "description": anomaly["description"],
                    "timestamp": anomaly["timestamp"],
                    "district": zone["name"],
                    "acknowledged": anomaly.get("acknowledged", False),
                }
            )

        return result

    @staticmethod
    async def get_region_statuses(
        db: Optional[AsyncSession] = None, anomaly_points: Optional[List[Dict]] = None
    ) -> List[Dict[str, Any]]:
        """
        Compute per-zone health scores by aggregating projected anomaly data.
        Returns zone status records including polygon boundary, health score, risk level.
        """
        if anomaly_points is None:
            anomaly_points = await GeoService.get_anomaly_points(db)

        # Group anomalies by district
        zone_anomalies: Dict[str, List[Dict]] = {z["region_id"]: [] for z in CITY_ZONES}
        for point in anomaly_points:
            # Match anomaly's district to a zone_id
            zone_id = next(
                (z["region_id"] for z in CITY_ZONES if z["name"] == point["district"]),
                "central_grid",
            )
            zone_anomalies[zone_id].append(point)

        regions = []
        for zone in CITY_ZONES:
            zone_points = zone_anomalies[zone["region_id"]]
            health_score, risk_level = _health_from_anomalies(zone_points)

            # Find dominant category
            cat_counts: Dict[str, int] = {}
            for p in zone_points:
                cat_counts[p["category"]] = cat_counts.get(p["category"], 0) + 1
            dominant = (
                max(cat_counts, key=cat_counts.get)
                if cat_counts
                else zone["primary_categories"][0]
            )

            critical_count = len(
                [p for p in zone_points if p["severity"] == "CRITICAL"]
            )

            regions.append(
                {
                    "region_id": zone["region_id"],
                    "name": zone["name"],
                    "centroid_lat": zone["centroid"][0],
                    "centroid_lng": zone["centroid"][1],
                    "health_score": health_score,
                    "risk_level": risk_level,
                    "anomaly_count": len(zone_points),
                    "critical_count": critical_count,
                    "dominant_category": dominant,
                    "polygon": zone["polygon"],
                }
            )

        return regions

    @staticmethod
    async def get_heatmap_points(
        db: Optional[AsyncSession] = None, anomaly_points: Optional[List[Dict]] = None
    ) -> List[Dict[str, Any]]:
        """
        Generate a weighted heatmap grid by spreading anomaly intensity across the city.
        Each anomaly contributes a cluster of surrounding weighted points.
        """
        if anomaly_points is None:
            anomaly_points = await GeoService.get_anomaly_points(db)

        heatmap = []

        for point in anomaly_points:
            base_intensity = _severity_weight(point["severity"]) * point["score"]

            # Core anomaly point at full intensity
            heatmap.append(
                {
                    "lat": point["lat"],
                    "lng": point["lng"],
                    "intensity": round(base_intensity, 3),
                }
            )

            # Emanating halo points at reduced intensity
            for i in range(4):
                angle = (i * 90) * math.pi / 180
                spread = 0.008
                h = {
                    "lat": round(point["lat"] + math.sin(angle) * spread, 6),
                    "lng": round(point["lng"] + math.cos(angle) * spread, 6),
                    "intensity": round(base_intensity * 0.45, 3),
                }
                heatmap.append(h)

        # Add zone centroid background ambience (low-intensity baseline)
        for zone in CITY_ZONES:
            lat, lng = zone["centroid"]
            heatmap.append(
                {
                    "lat": round(lat, 6),
                    "lng": round(lng, 6),
                    "intensity": 0.08,
                }
            )

        return heatmap

    @staticmethod
    async def get_full_map(db: Optional[AsyncSession] = None) -> Dict[str, Any]:
        """
        Master aggregator: returns the complete geospatial map payload
        including anomaly points, heatmap grid, and regional status.
        """
        anomaly_points = await GeoService.get_anomaly_points(db)
        regions = await GeoService.get_region_statuses(db, anomaly_points)
        heatmap_points = await GeoService.get_heatmap_points(db, anomaly_points)

        critical_count = len([p for p in anomaly_points if p["severity"] == "CRITICAL"])

        # Find most affected region (lowest health score)
        most_affected = (
            min(regions, key=lambda r: r["health_score"]) if regions else None
        )

        return {
            "anomaly_points": anomaly_points,
            "regions": regions,
            "heatmap_points": heatmap_points,
            "total_anomalies": len(anomaly_points),
            "critical_count": critical_count,
            "most_affected_region": most_affected["name"] if most_affected else None,
            "last_updated": datetime.utcnow().isoformat(),
        }
