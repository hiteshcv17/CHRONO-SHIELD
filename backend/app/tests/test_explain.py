"""
Phase 28 — Explainable AI Reasoning System Tests
Covers: service-layer causal analysis, NL generation, correlation chain,
reasoning steps, batch explain, and REST API endpoints.
"""
import pytest
import asyncio
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.services.explain_service import ExplainService


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


# ==============================================================================
# ── Service layer ─────────────────────────────────────────────────────────────
# ==============================================================================
class TestExplainService:

    # ── Output structure ──────────────────────────────────────────────────
    def test_output_has_required_fields(self):
        result = ExplainService.explain_anomaly(
            anomaly_id="TEST-001", metric_name="power_outage",
            severity="CRITICAL", category="POWER", score=0.92,
            timestamp="2026-05-28T14:30:00", district="East Industrial",
        )
        required = [
            "anomaly_id", "metric_name", "severity", "category", "timestamp",
            "district", "score", "headline", "summary", "causal_narrative",
            "contributing_factors", "correlation_chain", "reasoning_steps",
            "overall_confidence", "explanation_quality", "primary_cause",
            "cascade_risk", "impacted_systems", "recommended_actions",
            "ai_model_version", "explanation_latency_ms",
        ]
        for field in required:
            assert field in result, f"Missing field: {field}"

    def test_headline_contains_metric_and_district(self):
        result = ExplainService.explain_anomaly(
            anomaly_id="TEST-002", metric_name="traffic_jam",
            severity="WARNING", category="TRAFFIC", score=0.72,
            timestamp="2026-05-28T08:30:00", district="Central Grid",
        )
        assert "traffic" in result["headline"].lower() or "congestion" in result["headline"].lower()
        assert "Central Grid" in result["headline"]

    def test_headline_is_natural_language_sentence(self):
        result = ExplainService.explain_anomaly(
            anomaly_id="TEST-003", metric_name="water_pressure",
            severity="CRITICAL", category="WATER", score=0.90,
            timestamp="2026-05-28T18:00:00", district="South Harbor",
        )
        headline = result["headline"]
        assert len(headline) > 30, "Headline too short to be natural language"
        assert headline[-1] == ".", "Headline should end with a period"

    def test_causal_narrative_mentions_time_and_district(self):
        result = ExplainService.explain_anomaly(
            anomaly_id="TEST-004", metric_name="energy_demand",
            severity="CRITICAL", category="POWER", score=0.96,
            timestamp="2026-05-28T14:14:00", district="North District",
        )
        assert "North District" in result["causal_narrative"]
        assert "14:14" in result["causal_narrative"]

    def test_causal_narrative_length_sufficient(self):
        result = ExplainService.explain_anomaly(
            anomaly_id="TEST-005", metric_name="network_packet_loss",
            severity="CRITICAL", category="INTERNET", score=0.88,
            timestamp="2026-05-28T10:00:00", district="West Residential",
        )
        assert len(result["causal_narrative"]) > 200, "Causal narrative too short"

    # ── Contributing factors ──────────────────────────────────────────────
    def test_at_least_one_factor(self):
        result = ExplainService.explain_anomaly(
            anomaly_id="T1", metric_name="power_outage",
            severity="CRITICAL", category="POWER", score=0.85,
            timestamp="2026-05-28T07:30:00", district="East Industrial",
        )
        assert len(result["contributing_factors"]) >= 1

    def test_first_factor_is_primary(self):
        result = ExplainService.explain_anomaly(
            anomaly_id="T2", metric_name="traffic_accident",
            severity="CRITICAL", category="TRAFFIC", score=0.89,
            timestamp="2026-05-28T08:00:00", district="North District",
        )
        assert result["contributing_factors"][0]["factor_type"] == "PRIMARY"

    def test_factor_confidence_in_range(self):
        result = ExplainService.explain_anomaly(
            anomaly_id="T3", metric_name="water_quality",
            severity="CRITICAL", category="WATER", score=0.91,
            timestamp="2026-05-28T09:00:00", district="Central Grid",
        )
        for f in result["contributing_factors"]:
            assert 0.0 <= f["confidence"] <= 1.0, f"Out of range confidence: {f['confidence']}"

    def test_factor_weight_in_range(self):
        result = ExplainService.explain_anomaly(
            anomaly_id="T4", metric_name="grid_voltage",
            severity="WARNING", category="POWER", score=0.65,
            timestamp="2026-05-28T16:00:00", district="East Industrial",
        )
        for f in result["contributing_factors"]:
            assert 0.0 <= f["weight"] <= 1.0, f"Out of range weight: {f['weight']}"

    def test_factor_has_evidence(self):
        result = ExplainService.explain_anomaly(
            anomaly_id="T5", metric_name="power_outage",
            severity="CRITICAL", category="POWER", score=0.93,
            timestamp="2026-05-28T02:15:00", district="East Industrial",
        )
        for f in result["contributing_factors"]:
            assert len(f["evidence"]) > 0, f"Factor {f['factor_id']} has no evidence"

    def test_temporal_factor_present_during_peak(self):
        # Morning rush should add a TEMPORAL factor
        result = ExplainService.explain_anomaly(
            anomaly_id="T6", metric_name="traffic_jam",
            severity="WARNING", category="TRAFFIC", score=0.72,
            timestamp="2026-05-28T07:30:00", district="Central Grid",
        )
        types = [f["factor_type"] for f in result["contributing_factors"]]
        assert "TEMPORAL" in types, "Expected TEMPORAL factor during morning rush"

    def test_correlate_factors_exist_for_power(self):
        result = ExplainService.explain_anomaly(
            anomaly_id="T7", metric_name="power_outage",
            severity="CRITICAL", category="POWER", score=0.92,
            timestamp="2026-05-28T02:15:00", district="East Industrial",
        )
        types = [f["factor_type"] for f in result["contributing_factors"]]
        assert "CORRELATE" in types, "POWER anomaly should have cross-domain CORRELATE factors"

    def test_all_factor_categories_valid(self):
        valid_categories = {"POWER", "TRAFFIC", "WATER", "INTERNET", "PUBLIC_INFRASTRUCTURE", "WEATHER", "TEMPORAL"}
        result = ExplainService.explain_anomaly(
            anomaly_id="T8", metric_name="internet_bandwidth",
            severity="CRITICAL", category="INTERNET", score=0.92,
            timestamp="2026-05-28T13:40:00", district="North District",
        )
        for f in result["contributing_factors"]:
            assert f["category"] in valid_categories, f"Invalid category: {f['category']}"

    # ── Correlation chain ──────────────────────────────────────────────────
    def test_correlation_chain_is_list(self):
        result = ExplainService.explain_anomaly(
            anomaly_id="T9", metric_name="power_outage",
            severity="CRITICAL", category="POWER", score=0.88,
            timestamp="2026-05-28T02:00:00", district="East Industrial",
        )
        assert isinstance(result["correlation_chain"], list)

    def test_correlation_chain_relationships_valid(self):
        valid_rels = {"CAUSED", "AMPLIFIED", "CORRELATED", "PRECEDED", "TRIGGERED"}
        result = ExplainService.explain_anomaly(
            anomaly_id="T10", metric_name="power_outage",
            severity="CRITICAL", category="POWER", score=0.92,
            timestamp="2026-05-28T02:00:00", district="East Industrial",
        )
        for link in result["correlation_chain"]:
            assert link["relationship"] in valid_rels

    def test_correlation_strength_in_range(self):
        result = ExplainService.explain_anomaly(
            anomaly_id="T11", metric_name="power_outage",
            severity="CRITICAL", category="POWER", score=0.90,
            timestamp="2026-05-28T02:00:00", district="East Industrial",
        )
        for link in result["correlation_chain"]:
            assert 0.0 <= link["strength"] <= 1.0

    # ── Reasoning steps ────────────────────────────────────────────────────
    def test_exactly_five_reasoning_steps(self):
        result = ExplainService.explain_anomaly(
            anomaly_id="T12", metric_name="water_pressure",
            severity="CRITICAL", category="WATER", score=0.94,
            timestamp="2026-05-28T18:45:00", district="South Harbor",
        )
        assert len(result["reasoning_steps"]) == 5

    def test_reasoning_steps_ordered(self):
        result = ExplainService.explain_anomaly(
            anomaly_id="T13", metric_name="cpu_usage",
            severity="WARNING", category="INTERNET", score=0.77,
            timestamp="2026-05-28T12:05:00", district="Central Grid",
        )
        indices = [s["step_index"] for s in result["reasoning_steps"]]
        assert indices == sorted(indices)

    def test_reasoning_step_types_complete(self):
        expected = {"OBSERVE", "HYPOTHESIZE", "CORRELATE", "CONCLUDE", "RECOMMEND"}
        result = ExplainService.explain_anomaly(
            anomaly_id="T14", metric_name="traffic_accident",
            severity="CRITICAL", category="TRAFFIC", score=0.89,
            timestamp="2026-05-28T08:00:00", district="North District",
        )
        actual = {s["step_type"] for s in result["reasoning_steps"]}
        assert actual == expected

    def test_reasoning_step_confidence_in_range(self):
        result = ExplainService.explain_anomaly(
            anomaly_id="T15", metric_name="power_outage",
            severity="CRITICAL", category="POWER", score=0.93,
            timestamp="2026-05-28T02:15:00", district="East Industrial",
        )
        for step in result["reasoning_steps"]:
            assert 0.0 <= step["confidence"] <= 1.0

    # ── Confidence & quality ───────────────────────────────────────────────
    def test_overall_confidence_in_range(self):
        for score in [0.3, 0.6, 0.9]:
            result = ExplainService.explain_anomaly(
                anomaly_id=f"T-{score}", metric_name="power_outage",
                severity="CRITICAL", category="POWER", score=score,
                timestamp="2026-05-28T14:00:00", district="East Industrial",
            )
            assert 0.0 <= result["overall_confidence"] <= 1.0

    def test_high_score_yields_strong_or_moderate_quality(self):
        result = ExplainService.explain_anomaly(
            anomaly_id="T16", metric_name="energy_demand",
            severity="CRITICAL", category="POWER", score=0.96,
            timestamp="2026-05-28T15:00:00", district="North District",
        )
        assert result["explanation_quality"] in ("STRONG", "MODERATE")

    def test_low_score_may_yield_speculative(self):
        result = ExplainService.explain_anomaly(
            anomaly_id="T17", metric_name="infrastructure_defect",
            severity="INFO", category="PUBLIC_INFRASTRUCTURE", score=0.10,
            timestamp="2026-05-28T10:00:00", district="West Residential",
        )
        # Should be speculative or moderate (not guaranteed strong)
        assert result["explanation_quality"] in ("SPECULATIVE", "MODERATE")

    def test_cascade_risk_valid(self):
        valid_risks = {"LOW", "MODERATE", "HIGH", "CRITICAL"}
        result = ExplainService.explain_anomaly(
            anomaly_id="T18", metric_name="water_quality",
            severity="CRITICAL", category="WATER", score=0.91,
            timestamp="2026-05-28T09:00:00", district="Central Grid",
        )
        assert result["cascade_risk"] in valid_risks

    def test_recommended_actions_nonempty(self):
        result = ExplainService.explain_anomaly(
            anomaly_id="T19", metric_name="network_latency",
            severity="WARNING", category="INTERNET", score=0.65,
            timestamp="2026-05-28T11:00:00", district="North District",
        )
        assert len(result["recommended_actions"]) > 0

    def test_impacted_systems_nonempty(self):
        result = ExplainService.explain_anomaly(
            anomaly_id="T20", metric_name="power_outage",
            severity="CRITICAL", category="POWER", score=0.93,
            timestamp="2026-05-28T02:15:00", district="East Industrial",
        )
        assert len(result["impacted_systems"]) > 0

    def test_ai_model_version_set(self):
        result = ExplainService.explain_anomaly(
            anomaly_id="T21", metric_name="power_outage",
            severity="CRITICAL", category="POWER", score=0.93,
            timestamp="2026-05-28T02:15:00", district="East Industrial",
        )
        assert result["ai_model_version"] == "ChronoShield-XAI-v2.4"

    def test_latency_measured(self):
        result = ExplainService.explain_anomaly(
            anomaly_id="T22", metric_name="traffic_jam",
            severity="WARNING", category="TRAFFIC", score=0.72,
            timestamp="2026-05-28T07:30:00", district="Central Grid",
        )
        assert result["explanation_latency_ms"] >= 0

    # ── Fallback behaviour for unknown metric ──────────────────────────────
    def test_unknown_metric_fallback(self):
        result = ExplainService.explain_anomaly(
            anomaly_id="T23", metric_name="mystery_sensor_x99",
            severity="WARNING", category="PUBLIC_INFRASTRUCTURE", score=0.55,
            timestamp="2026-05-28T10:00:00", district="West Residential",
        )
        assert len(result["contributing_factors"]) >= 1
        assert len(result["headline"]) > 10
        assert len(result["recommended_actions"]) > 0

    # ── Batch explain ──────────────────────────────────────────────────────
    def test_batch_explain_returns_all(self):
        anomalies = [
            {"anomaly_id": "B001", "metric_name": "power_outage", "severity": "CRITICAL", "category": "POWER", "score": 0.92, "timestamp": "2026-05-28T02:15:00", "district": "East Industrial"},
            {"anomaly_id": "B002", "metric_name": "internet_bandwidth", "severity": "CRITICAL", "category": "INTERNET", "score": 0.92, "timestamp": "2026-05-28T13:40:00", "district": "North District"},
        ]
        result = ExplainService.explain_batch(anomalies)
        assert result["total_analyzed"] == 2
        assert len(result["explanations"]) == 2

    def test_batch_cross_incident_patterns_list(self):
        anomalies = [
            {"anomaly_id": "B003", "metric_name": "power_outage", "severity": "CRITICAL", "category": "POWER", "score": 0.92, "timestamp": "2026-05-28T02:15:00", "district": "East Industrial"},
            {"anomaly_id": "B004", "metric_name": "network_packet_loss", "severity": "CRITICAL", "category": "INTERNET", "score": 0.88, "timestamp": "2026-05-28T02:18:00", "district": "East Industrial"},
        ]
        result = ExplainService.explain_batch(anomalies)
        assert isinstance(result["cross_incident_patterns"], list)
        assert len(result["cross_incident_patterns"]) > 0  # POWER+INTERNET pattern detected

    def test_batch_system_narrative_nonempty(self):
        anomalies = [
            {"anomaly_id": "B005", "metric_name": "traffic_jam", "severity": "WARNING", "category": "TRAFFIC", "score": 0.72, "timestamp": "2026-05-28T08:00:00", "district": "Central Grid"},
            {"anomaly_id": "B006", "metric_name": "traffic_accident", "severity": "CRITICAL", "category": "TRAFFIC", "score": 0.89, "timestamp": "2026-05-28T08:05:00", "district": "North District"},
        ]
        result = ExplainService.explain_batch(anomalies)
        assert len(result["system_narrative"]) > 50

    def test_batch_high_confidence_count(self):
        anomalies = [
            {"anomaly_id": "B007", "metric_name": "power_outage", "severity": "CRITICAL", "category": "POWER", "score": 0.95, "timestamp": "2026-05-28T14:00:00", "district": "East Industrial"},
        ]
        result = ExplainService.explain_batch(anomalies)
        assert result["high_confidence_count"] >= 0
        assert result["high_confidence_count"] <= result["total_analyzed"]


# ==============================================================================
# ── REST API tests ─────────────────────────────────────────────────────────────
# ==============================================================================
class TestExplainAPI:

    def test_preview_endpoint_ok(self):
        async def _run():
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.get("/api/v1/explain/preview")
                assert resp.status_code == 200
                data = resp.json()
                assert "headline" in data
                assert "contributing_factors" in data
        asyncio.get_event_loop().run_until_complete(_run())

    def test_anomaly_endpoint_ok(self):
        async def _run():
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                payload = {
                    "anomaly_id": "API-001", "metric_name": "traffic_accident",
                    "severity": "CRITICAL", "category": "TRAFFIC", "score": 0.89,
                    "timestamp": "2026-05-28T08:00:00", "district": "North District",
                }
                resp = await client.post("/api/v1/explain/anomaly", json=payload)
                assert resp.status_code == 200
                data = resp.json()
                assert data["anomaly_id"] == "API-001"
                assert "causal_narrative" in data
                assert "reasoning_steps" in data
        asyncio.get_event_loop().run_until_complete(_run())

    def test_batch_endpoint_ok(self):
        async def _run():
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                payload = {"anomalies": [
                    {"anomaly_id": "API-002", "metric_name": "power_outage", "severity": "CRITICAL", "category": "POWER", "score": 0.93, "timestamp": "2026-05-28T02:15:00", "district": "East Industrial"},
                    {"anomaly_id": "API-003", "metric_name": "internet_bandwidth", "severity": "CRITICAL", "category": "INTERNET", "score": 0.92, "timestamp": "2026-05-28T13:40:00", "district": "North District"},
                ]}
                resp = await client.post("/api/v1/explain/batch", json=payload)
                assert resp.status_code == 200
                data = resp.json()
                assert data["total_analyzed"] == 2
                assert len(data["explanations"]) == 2
        asyncio.get_event_loop().run_until_complete(_run())

    def test_preview_custom_metric(self):
        async def _run():
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.get("/api/v1/explain/preview?metric=water_quality&category=WATER&score=0.91&severity=CRITICAL")
                assert resp.status_code == 200
                data = resp.json()
                assert "water" in data["headline"].lower() or "quality" in data["headline"].lower()
        asyncio.get_event_loop().run_until_complete(_run())

    def test_openapi_registers_explain_tag(self):
        async def _run():
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.get("/openapi.json")
                assert resp.status_code == 200
                spec = resp.json()
                assert "/api/v1/explain/preview" in spec["paths"]
        asyncio.get_event_loop().run_until_complete(_run())
