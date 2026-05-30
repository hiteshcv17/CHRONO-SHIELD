"""
Phase 26 — Geospatial Infrastructure Visualization
Automated verification suite for geo_service projection engine and REST API endpoints.
"""

import asyncio
from fastapi.testclient import TestClient
from app.services.geo_service import (
    GeoService,
    CITY_ZONES,
    _infer_category,
    _jitter_coords,
    _health_from_anomalies,
)


# ==============================================================================
# Unit Tests — GeoService Core Logic
# ==============================================================================


class TestGeoProjection:
    """Verify anomaly geo-projection, deterministic jitter, and health scoring."""

    def _run_async(self, coro):
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)

    def test_category_inference(self):
        """Assert keyword-based category mapping is correct for all domain types."""
        assert _infer_category("energy_demand") == "POWER"
        assert _infer_category("power_outage") == "POWER"
        assert _infer_category("grid_voltage") == "POWER"
        assert _infer_category("traffic_jam") == "TRAFFIC"
        assert _infer_category("vehicle_count") == "TRAFFIC"
        assert _infer_category("water_pressure") == "WATER"
        assert _infer_category("flood_sensor") == "WATER"
        assert _infer_category("network_latency") == "INTERNET"
        assert _infer_category("cpu_usage") == "INTERNET"
        assert _infer_category("road_signal") == "PUBLIC_INFRASTRUCTURE"
        assert _infer_category("infrastructure_defect") == "PUBLIC_INFRASTRUCTURE"

    def test_coordinate_jitter_determinism(self):
        """Assert same seed always produces same coordinate offset."""
        lat1, lng1 = _jitter_coords(28.6304, 77.2177, "seed-abc")
        lat2, lng2 = _jitter_coords(28.6304, 77.2177, "seed-abc")
        assert lat1 == lat2
        assert lng1 == lng2

    def test_coordinate_jitter_spread(self):
        """Assert jittered coordinates are within reasonable distance from centroid."""
        base_lat, base_lng = 28.6304, 77.2177
        lat, lng = _jitter_coords(base_lat, base_lng, "spread-test", scale=0.018)
        assert abs(lat - base_lat) < 0.02
        assert abs(lng - base_lng) < 0.02

    def test_health_score_nominal(self):
        """Assert empty zone returns high health score and NOMINAL risk."""
        score, risk = _health_from_anomalies([])
        assert score >= 80.0
        assert risk == "NOMINAL"

    def test_health_score_critical(self):
        """Assert multiple critical anomalies drive down health score."""
        anomalies = [{"severity": "CRITICAL", "score": 0.95} for _ in range(5)]
        score, risk = _health_from_anomalies(anomalies)
        assert score < 45.0
        assert risk in ["HIGH", "CRITICAL"]

    def test_health_score_bounds(self):
        """Assert health score is always within [5, 100]."""
        for count in [0, 1, 3, 10, 20]:
            anomalies = [{"severity": "CRITICAL", "score": 1.0} for _ in range(count)]
            score, _ = _health_from_anomalies(anomalies)
            assert 5.0 <= score <= 100.0

    def test_city_zones_count(self):
        """Assert exactly 5 city zones are defined with required fields."""
        assert len(CITY_ZONES) == 5
        for zone in CITY_ZONES:
            assert "region_id" in zone
            assert "name" in zone
            assert "centroid" in zone
            assert "polygon" in zone
            assert len(zone["polygon"]) >= 4  # Closed polygon has at least 4 points

    def test_anomaly_points_no_db(self):
        """Assert mock anomaly dataset is projected correctly without a DB session."""
        points = self._run_async(GeoService.get_anomaly_points(db=None))
        assert len(points) >= 10

        for p in points:
            assert "id" in p
            assert "lat" in p
            assert "lng" in p
            assert "severity" in p
            assert "category" in p
            assert "score" in p
            assert "metric_name" in p
            assert "description" in p
            assert "district" in p
            assert p["severity"] in ["CRITICAL", "WARNING", "INFO"]
            assert p["category"] in [
                "POWER",
                "TRAFFIC",
                "WATER",
                "INTERNET",
                "PUBLIC_INFRASTRUCTURE",
            ]
            assert 0.0 <= p["score"] <= 1.0

    def test_anomaly_points_lat_lng_in_city_range(self):
        """Assert all projected coordinates fall within the broader city bounding box."""
        points = self._run_async(GeoService.get_anomaly_points(db=None))
        for p in points:
            assert 28.40 <= p["lat"] <= 28.80, f"Lat out of range: {p['lat']}"
            assert 76.90 <= p["lng"] <= 77.55, f"Lng out of range: {p['lng']}"

    def test_region_statuses_no_db(self):
        """Assert region status computation returns all 5 zones with valid fields."""
        regions = self._run_async(GeoService.get_region_statuses(db=None))
        assert len(regions) == 5

        for r in regions:
            assert "region_id" in r
            assert "name" in r
            assert "health_score" in r
            assert 5.0 <= r["health_score"] <= 100.0
            assert "risk_level" in r
            assert r["risk_level"] in ["NOMINAL", "LOW", "MEDIUM", "HIGH", "CRITICAL"]
            assert "anomaly_count" in r
            assert r["anomaly_count"] >= 0
            assert "polygon" in r
            assert len(r["polygon"]) >= 4

    def test_heatmap_points_no_db(self):
        """Assert heatmap generation returns valid intensity-weighted points."""
        points = self._run_async(GeoService.get_heatmap_points(db=None))
        assert len(points) >= 5  # At least zone centroids

        for p in points:
            assert "lat" in p
            assert "lng" in p
            assert "intensity" in p
            assert 0.0 <= p["intensity"] <= 1.0

    def test_full_map_no_db(self):
        """Assert full map aggregator returns valid composite payload."""
        data = self._run_async(GeoService.get_full_map(db=None))
        assert "anomaly_points" in data
        assert "regions" in data
        assert "heatmap_points" in data
        assert "total_anomalies" in data
        assert "critical_count" in data
        assert "most_affected_region" in data
        assert "last_updated" in data

        assert isinstance(data["anomaly_points"], list)
        assert isinstance(data["regions"], list)
        assert isinstance(data["heatmap_points"], list)
        assert data["total_anomalies"] == len(data["anomaly_points"])
        assert data["critical_count"] >= 0
        assert data["critical_count"] <= data["total_anomalies"]


# ==============================================================================
# Integration Tests — REST API Endpoints
# ==============================================================================


class TestGeoAPI:
    """Verify geospatial REST API endpoints return valid schemas."""

    @classmethod
    def setup_class(cls):
        from app.main import app

        cls.client = TestClient(app)

    def test_get_geo_map_api(self):
        """Assert GET /api/v1/geo/map returns valid GeoMapResponse."""
        response = self.client.get("/api/v1/geo/map")
        assert response.status_code == 200
        data = response.json()

        assert "anomaly_points" in data
        assert "regions" in data
        assert "heatmap_points" in data
        assert "total_anomalies" in data
        assert "critical_count" in data
        assert isinstance(data["anomaly_points"], list)
        assert len(data["anomaly_points"]) > 0
        assert len(data["regions"]) == 5
        assert len(data["heatmap_points"]) > 0

    def test_get_geo_anomaly_points_api(self):
        """Assert GET /api/v1/geo/anomaly-points returns valid list."""
        response = self.client.get("/api/v1/geo/anomaly-points")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

        for point in data:
            assert "id" in point
            assert "lat" in point
            assert "lng" in point
            assert "severity" in point
            assert "category" in point
            assert "score" in point
            assert 0.0 <= point["score"] <= 1.0

    def test_get_geo_anomaly_points_severity_filter(self):
        """Assert severity filter narrows returned anomaly list correctly."""
        response = self.client.get("/api/v1/geo/anomaly-points?severity=CRITICAL")
        assert response.status_code == 200
        data = response.json()
        for point in data:
            assert point["severity"] == "CRITICAL"

    def test_get_geo_anomaly_points_category_filter(self):
        """Assert category filter narrows returned anomaly list correctly."""
        response = self.client.get("/api/v1/geo/anomaly-points?category=POWER")
        assert response.status_code == 200
        data = response.json()
        for point in data:
            assert point["category"] == "POWER"

    def test_get_geo_regions_api(self):
        """Assert GET /api/v1/geo/regions returns all 5 zones with health data."""
        response = self.client.get("/api/v1/geo/regions")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 5

        for region in data:
            assert "region_id" in region
            assert "name" in region
            assert "health_score" in region
            assert "risk_level" in region
            assert "polygon" in region
            assert 5.0 <= region["health_score"] <= 100.0
            assert region["risk_level"] in [
                "NOMINAL",
                "LOW",
                "MEDIUM",
                "HIGH",
                "CRITICAL",
            ]
            assert len(region["polygon"]) >= 4

    def test_get_geo_heatmap_api(self):
        """Assert GET /api/v1/geo/heatmap returns intensity-normalized grid."""
        response = self.client.get("/api/v1/geo/heatmap")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

        for point in data:
            assert "lat" in point
            assert "lng" in point
            assert "intensity" in point
            assert 0.0 <= point["intensity"] <= 1.0

    def test_geo_map_region_ids_unique(self):
        """Assert all returned region_ids are unique (no duplicates)."""
        response = self.client.get("/api/v1/geo/regions")
        data = response.json()
        ids = [r["region_id"] for r in data]
        assert len(ids) == len(set(ids))

    def test_geo_total_anomalies_consistency(self):
        """Assert total_anomalies matches actual anomaly_points list length."""
        response = self.client.get("/api/v1/geo/map")
        data = response.json()
        assert data["total_anomalies"] == len(data["anomaly_points"])

    def test_geo_critical_count_consistency(self):
        """Assert critical_count matches actual critical anomaly count in list."""
        response = self.client.get("/api/v1/geo/map")
        data = response.json()
        actual_critical = len(
            [p for p in data["anomaly_points"] if p["severity"] == "CRITICAL"]
        )
        assert data["critical_count"] == actual_critical
