import asyncio
from app.services.health_service import HealthService


class TestHealthDiagnostics:

    def test_infrastructure_diagnostics_calculation(self):
        """Verify the health calculations, logistic failure probability curves, and risk tiers."""

        async def run_test():
            return await HealthService.get_infrastructure_diagnostics(None)

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        result = loop.run_until_complete(run_test())
        assert "overall_health_score" in result
        assert "active_risks_count" in result
        assert "reports" in result

        # At least 5 critical nodes must be classified
        assert len(result["reports"]) == 5

        # Verify node fields
        for r in result["reports"]:
            assert "name" in r
            assert "node_type" in r
            assert "health_score" in r
            assert 0 <= r["health_score"] <= 100
            assert "failure_probability" in r
            assert 0.0 <= r["failure_probability"] <= 100.0
            assert "remaining_useful_life_days" in r
            assert r["remaining_useful_life_days"] > 0
            assert "risk_tier" in r
            assert r["risk_tier"] in ["NOMINAL", "MEDIUM", "HIGH", "CRITICAL"]
            assert "explanation" in r

        # Verify specific stressed Redis parameters conform to targets
        redis_report = next(
            r for r in result["reports"] if r["name"] == "chronoshield-redis-cache"
        )
        assert redis_report["health_score"] <= 66
        assert redis_report["failure_probability"] >= 78.0
        assert redis_report["remaining_useful_life_days"] == 9
        assert redis_report["risk_tier"] == "CRITICAL"


class TestHealthAPI:
    """
    Verification suite testing infrastructure health endpoints, dynamic health scores,
    and multi-source risk aggregation results.
    """

    @classmethod
    def setup_class(cls):
        from fastapi.testclient import TestClient
        from app.main import app

        cls.client = TestClient(app)

    def test_get_city_health_components_api(self):
        """Assert GET /api/v1/health/components returns valid dynamic scores for all 5 sectors."""
        response = self.client.get("/api/v1/health/components")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "reports" in data

        # Check all 5 sectors are represented
        categories = {r["category"] for r in data["reports"]}
        assert categories == {
            "POWER",
            "TRAFFIC",
            "WATER",
            "INTERNET",
            "PUBLIC_INFRASTRUCTURE",
        }

        for report in data["reports"]:
            assert "category" in report
            assert "health_score" in report
            assert 5 <= report["health_score"] <= 100
            assert "risk_level" in report
            assert report["risk_level"] in [
                "NOMINAL",
                "LOW",
                "MEDIUM",
                "HIGH",
                "CRITICAL",
            ]
            assert "confidence_score" in report
            assert 20 <= report["confidence_score"] <= 100
            assert "metrics" in report
            assert "penalties_breakdown" in report
            assert "explanation" in report

            # Verify penalties exist
            penalties = report["penalties_breakdown"]
            assert "anomaly_penalty" in penalties
            assert "social_penalty" in penalties
            assert "physical_penalty" in penalties
            assert penalties["anomaly_penalty"] >= 0.0
            assert penalties["social_penalty"] >= 0.0
            assert penalties["physical_penalty"] >= 0.0

    def test_get_infrastructure_diagnostics_api(self):
        """Assert original cluster node diagnostics GET /api/v1/health/diagnose returns correctly."""
        response = self.client.get("/api/v1/health/diagnose")
        assert response.status_code == 200
        data = response.json()
        assert "overall_health_score" in data
        assert "active_risks_count" in data
        assert "reports" in data
        assert len(data["reports"]) == 5
