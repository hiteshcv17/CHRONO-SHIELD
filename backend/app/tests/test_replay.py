"""
Phase 27 — Historical Replay & Incident Timeline Analysis Tests
Covers: timeline generation, bucket structure, incident records, replay frames,
incident comparison, and REST API endpoints.
"""

import pytest
import asyncio
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.services.replay_service import ReplayService


# ==============================================================================
# Helpers
# ==============================================================================
def _run_async(coro):
    return asyncio.run(coro)


# ==============================================================================
# Service-layer tests
# ==============================================================================
class TestReplayService:
    def test_timeline_default_24h(self):
        data = ReplayService.get_timeline(time_range_hours=24)
        assert data["time_range_hours"] == 24
        assert data["bucket_duration_minutes"] == 30
        assert len(data["buckets"]) == 48  # 24h * 2 buckets/hr
        assert data["total_incidents"] > 0
        assert data["total_critical"] > 0

    def test_timeline_12h(self):
        data = ReplayService.get_timeline(time_range_hours=12)
        assert len(data["buckets"]) == 24  # 12h * 2

    def test_bucket_structure(self):
        data = ReplayService.get_timeline(24)
        bucket = data["buckets"][0]
        required = [
            "bucket_index",
            "timestamp_start",
            "timestamp_end",
            "label",
            "anomaly_count",
            "critical_count",
            "severity_distribution",
            "category_distribution",
            "peak_score",
            "health_delta",
            "event_ids",
        ]
        for field in required:
            assert field in bucket, f"Missing bucket field: {field}"

    def test_bucket_severity_distribution_structure(self):
        data = ReplayService.get_timeline(24)
        for bucket in data["buckets"]:
            sd = bucket["severity_distribution"]
            assert "CRITICAL" in sd
            assert "WARNING" in sd
            assert "INFO" in sd
            assert all(isinstance(v, int) for v in sd.values())

    def test_bucket_category_distribution_structure(self):
        data = ReplayService.get_timeline(24)
        for bucket in data["buckets"]:
            cd = bucket["category_distribution"]
            for cat in [
                "POWER",
                "TRAFFIC",
                "WATER",
                "INTERNET",
                "PUBLIC_INFRASTRUCTURE",
            ]:
                assert cat in cd

    def test_incident_record_structure(self):
        data = ReplayService.get_timeline(24)
        inc = data["incidents"][0]
        required = [
            "id",
            "timestamp",
            "metric_name",
            "severity",
            "category",
            "score",
            "description",
            "district",
            "acknowledged",
            "duration_minutes",
            "cascaded",
            "related_ids",
            "root_cause_hint",
            "resolution_hint",
            "bucket_index",
        ]
        for field in required:
            assert field in inc, f"Missing incident field: {field}"

    def test_incident_severity_valid(self):
        data = ReplayService.get_timeline(24)
        valid = {"CRITICAL", "WARNING", "INFO"}
        for inc in data["incidents"]:
            assert inc["severity"] in valid, f"Invalid severity: {inc['severity']}"

    def test_incident_category_valid(self):
        data = ReplayService.get_timeline(24)
        valid = {"POWER", "TRAFFIC", "WATER", "INTERNET", "PUBLIC_INFRASTRUCTURE"}
        for inc in data["incidents"]:
            assert inc["category"] in valid, f"Invalid category: {inc['category']}"

    def test_incident_score_range(self):
        data = ReplayService.get_timeline(24)
        for inc in data["incidents"]:
            assert 0.0 <= inc["score"] <= 1.0, f"Score out of range: {inc['score']}"

    def test_incident_bucket_index_within_range(self):
        data = ReplayService.get_timeline(24)
        n_buckets = 48
        for inc in data["incidents"]:
            assert (
                0 <= inc["bucket_index"] < n_buckets
            ), f"Incident {inc['id']} has out-of-range bucket_index {inc['bucket_index']}"

    def test_peak_bucket_valid(self):
        data = ReplayService.get_timeline(24)
        assert 0 <= data["peak_bucket_index"] < len(data["buckets"])

    def test_cascade_pairs_set(self):
        data = ReplayService.get_timeline(24)
        cascades = {i["id"]: i for i in data["incidents"]}
        # INC-005 caused INC-006 — INC-006 should list INC-005 as related
        assert "INC-006" in cascades
        assert "INC-005" in cascades["INC-006"]["related_ids"]

    def test_bucket_event_ids_match_incidents(self):
        data = ReplayService.get_timeline(24)
        all_ids = {i["id"] for i in data["incidents"]}
        for bucket in data["buckets"]:
            for eid in bucket["event_ids"]:
                assert (
                    eid in all_ids
                ), f"Event ID {eid} in bucket not found in incidents"

    def test_replay_frame_structure(self):
        data = ReplayService.get_timeline(24)
        frame = ReplayService.get_replay_frame(10, data["incidents"])
        required = [
            "bucket",
            "active_incidents",
            "cumulative_critical",
            "cumulative_total",
            "system_health",
            "dominant_category",
            "alert_level",
        ]
        for field in required:
            assert field in frame, f"Missing frame field: {field}"

    def test_replay_frame_health_range(self):
        data = ReplayService.get_timeline(24)
        for idx in [0, 10, 24, 47]:
            frame = ReplayService.get_replay_frame(idx, data["incidents"])
            assert 0 <= frame["system_health"] <= 100

    def test_replay_frame_alert_level_valid(self):
        data = ReplayService.get_timeline(24)
        valid = {"NOMINAL", "ELEVATED", "HIGH", "CRISIS"}
        for idx in [0, 15, 30, 47]:
            frame = ReplayService.get_replay_frame(idx, data["incidents"])
            assert frame["alert_level"] in valid

    def test_replay_frame_cumulative_monotonic(self):
        data = ReplayService.get_timeline(24)
        totals = [
            ReplayService.get_replay_frame(i, data["incidents"])["cumulative_total"]
            for i in [0, 10, 24, 47]
        ]
        assert totals == sorted(
            totals
        ), "Cumulative total should be monotonically non-decreasing"

    def test_compare_incidents_same(self):
        data = ReplayService.get_timeline(24)
        result = ReplayService.compare_incidents(
            "INC-017", "INC-018", data["incidents"]
        )
        assert result
        assert "similarity_score" in result
        assert 0.0 <= result["similarity_score"] <= 1.0

    def test_compare_incidents_correlated(self):
        data = ReplayService.get_timeline(24)
        # INC-005 (POWER) and INC-006 (INTERNET) — same district "East Industrial", 3min apart
        result = ReplayService.compare_incidents(
            "INC-005", "INC-006", data["incidents"]
        )
        # Same district + time_delta < 30min → correlated
        assert result["likely_correlated"] is True

    def test_compare_incidents_combined_risk(self):
        data = ReplayService.get_timeline(24)
        result = ReplayService.compare_incidents(
            "INC-032", "INC-030", data["incidents"]
        )
        assert result["combined_risk"] in {"MODERATE", "HIGH", "EXTREME"}

    def test_compare_incidents_missing_returns_empty(self):
        data = ReplayService.get_timeline(24)
        result = ReplayService.compare_incidents(
            "INC-999", "INC-001", data["incidents"]
        )
        assert result == {}

    def test_peak_score_per_bucket(self):
        data = ReplayService.get_timeline(24)
        for bucket in data["buckets"]:
            assert 0.0 <= bucket["peak_score"] <= 1.0


# ==============================================================================
# REST API tests
# ==============================================================================
class TestReplayAPI:
    def test_timeline_endpoint_ok(self):
        async def _run():
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.get("/api/v1/replay/timeline")
                assert resp.status_code == 200
                data = resp.json()
                assert "buckets" in data
                assert "incidents" in data
                assert len(data["buckets"]) == 48

        _run_async(_run())

    def test_timeline_endpoint_12h(self):
        async def _run():
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.get("/api/v1/replay/timeline?hours=12")
                assert resp.status_code == 200
                data = resp.json()
                assert len(data["buckets"]) == 24

        _run_async(_run())

    def test_frame_endpoint_ok(self):
        async def _run():
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.get("/api/v1/replay/frame/15")
                assert resp.status_code == 200
                data = resp.json()
                assert "system_health" in data
                assert "alert_level" in data

        _run_async(_run())

    def test_compare_endpoint_ok(self):
        async def _run():
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.get(
                    "/api/v1/replay/compare?id_a=INC-005&id_b=INC-006"
                )
                assert resp.status_code == 200
                data = resp.json()
                assert "similarity_score" in data
                assert "combined_risk" in data

        _run_async(_run())

    def test_compare_endpoint_not_found(self):
        async def _run():
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.get(
                    "/api/v1/replay/compare?id_a=INC-999&id_b=INC-001"
                )
                assert resp.status_code == 404

        _run_async(_run())

    def test_timeline_tags_in_openapi(self):
        async def _run():
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.get("/openapi.json")
                assert resp.status_code == 200
                spec = resp.json()
                paths = spec.get("paths", {})
                assert "/api/v1/replay/timeline" in paths

        _run_async(_run())
