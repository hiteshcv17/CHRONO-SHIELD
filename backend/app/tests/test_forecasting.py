import asyncio
import pytest
from app.services.forecasting_service import ForecastingService


class TestForecastingPipeline:

    def _run_async(self, coro):
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)

    def test_24h_prophet_forecast(self):
        """Verify Prophet predictive pipelines for a 24-hour horizon."""
        async def run_test():
            return await ForecastingService.get_telemetry_forecast(None, "energy_demand", horizon_hours=24)
        
        result = self._run_async(run_test())
        assert result["metric_name"] == "Energy Demand (kW)"
        assert len(result["records"]) > 100
        assert "predicted_anomalies" in result
        assert "explanation" in result
        
        # Verify explanation schema
        expl = result["explanation"]
        assert expl["trend_direction"] in ["UPWARD_TREND", "DOWNWARD_TREND", "STABLE"]
        assert "trend_summary" in expl
        assert "peak_day_of_week" in expl
        assert "peak_hour_of_day" in expl
        assert len(expl["analysis_notes"]) == 3

    def test_7d_prophet_forecast(self):
        """Verify Prophet predictive pipelines for a 7-day (168-hour) horizon."""
        async def run_test():
            return await ForecastingService.get_telemetry_forecast(None, "traffic_jam", horizon_hours=168)
        
        result = self._run_async(run_test())
        assert result["metric_name"] == "Traffic Jam Factor"
        assert len(result["records"]) > 100
        
    def test_30d_prophet_forecast(self):
        """Verify Prophet predictive pipelines for a 30-day (720-hour) horizon."""
        async def run_test():
            return await ForecastingService.get_telemetry_forecast(None, "anomaly_score", horizon_hours=720)
        
        result = self._run_async(run_test())
        assert result["metric_name"] == "AI Anomaly Score"
        assert len(result["records"]) > 100

    def test_predict_endpoint_caching(self):
        """Verify that the /predict API endpoint caches results and serves hits quickly."""
        from fastapi.testclient import TestClient
        from fastapi import status
        from app.main import app
        from app.core.auth import get_current_user
        from app.db.session import get_db_session
        from app.models.user import User
        from app.utils.cache import invalidate_cache_by_pattern
        import time

        client = TestClient(app)

        # Mock dependencies
        mock_user = User(
            id="usr-mocked1",
            username="mockoperator",
            email="mock@chronoshield.ai",
            role="ANALYST",
            is_active=True
        )
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db_session] = lambda: None

        async def run_test():
            # Clear existing forecasting cache keys
            await invalidate_cache_by_pattern("forecast:*")

            # First request (cache miss)
            t0 = time.time()
            response1 = client.get("/api/v1/forecasting/predict?metric_id=energy_demand&horizon_hours=24")
            duration1 = time.time() - t0

            assert response1.status_code == status.HTTP_200_OK
            data1 = response1.json()
            assert data1["success"] is True

            # Second request (cache hit)
            t1 = time.time()
            response2 = client.get("/api/v1/forecasting/predict?metric_id=energy_demand&horizon_hours=24")
            duration2 = time.time() - t1

            assert response2.status_code == status.HTTP_200_OK
            data2 = response2.json()
            assert data2["success"] is True
            assert data2["metric_name"] == data1["metric_name"]
            assert len(data2["records"]) == len(data1["records"])

            # Verify cache hit is significantly faster
            assert duration2 < duration1
            assert duration2 < 0.05  # Cache hit should be under 50ms

        self._run_async(run_test())

        # Cleanup overrides
        if get_current_user in app.dependency_overrides:
            del app.dependency_overrides[get_current_user]
        if get_db_session in app.dependency_overrides:
            del app.dependency_overrides[get_db_session]


