import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.main import app
from app.core.auth import get_current_user
from app.db.session import get_db_session
from app.models.user import User

client = TestClient(app)

class TestRBAC:
    @pytest.fixture(autouse=True)
    def setup_overrides(self):
        # We don't need real db access for role checks since we override get_current_user
        app.dependency_overrides[get_db_session] = lambda: None
        yield
        if get_current_user in app.dependency_overrides:
            del app.dependency_overrides[get_current_user]
        if get_db_session in app.dependency_overrides:
            del app.dependency_overrides[get_db_session]

    def set_current_user_role(self, role: str):
        mock_user = User(
            id="usr-mocked1",
            username="mockoperator",
            email="mock@chronoshield.ai",
            role=role,
            is_active=True
        )
        app.dependency_overrides[get_current_user] = lambda: mock_user

    # ==========================================================================
    # 1. Admin Endpoints (e.g., Benchmark run / Auth register)
    # ==========================================================================
    def test_benchmark_admin_access(self):
        """Admin role can access benchmark endpoints."""
        self.set_current_user_role("ADMIN")
        # Send empty benchmark request to cause validation error instead of 403 Forbidden
        response = client.post("/api/v1/benchmark/run", json={})
        assert response.status_code != status.HTTP_403_FORBIDDEN

    def test_benchmark_analyst_denied(self):
        """Analyst role is blocked from benchmark endpoints with 403."""
        self.set_current_user_role("ANALYST")
        response = client.post("/api/v1/benchmark/run", json={})
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_benchmark_viewer_denied(self):
        """Viewer role is blocked from benchmark endpoints with 403."""
        self.set_current_user_role("VIEWER")
        response = client.post("/api/v1/benchmark/run", json={})
        assert response.status_code == status.HTTP_403_FORBIDDEN

    # ==========================================================================
    # 2. Analyst Endpoints (e.g., Forecasting predict)
    # ==========================================================================
    def test_forecasting_admin_access(self):
        """Admin role can access forecasting."""
        self.set_current_user_role("ADMIN")
        response = client.get("/api/v1/forecasting/predict")
        # Expect either 200 OK or 500/errors (but not 403 Forbidden)
        assert response.status_code != status.HTTP_403_FORBIDDEN

    def test_forecasting_analyst_access(self):
        """Analyst role can access forecasting."""
        self.set_current_user_role("ANALYST")
        response = client.get("/api/v1/forecasting/predict")
        assert response.status_code != status.HTTP_403_FORBIDDEN

    def test_forecasting_viewer_denied(self):
        """Viewer role is blocked from forecasting endpoints with 403."""
        self.set_current_user_role("VIEWER")
        response = client.get("/api/v1/forecasting/predict")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    # ==========================================================================
    # 3. Viewer/General Endpoints (e.g., Infrastructure Health diagnostics)
    # ==========================================================================
    def test_health_diagnose_all_roles_access(self):
        """Viewer, Analyst, and Admin roles can access general read-only endpoints."""
        for role in ["ADMIN", "ANALYST", "VIEWER"]:
            self.set_current_user_role(role)
            response = client.get("/api/v1/health/diagnose")
            assert response.status_code != status.HTTP_403_FORBIDDEN
