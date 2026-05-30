import os
import pytest
from fastapi import status
from fastapi.testclient import TestClient
from datetime import datetime, timedelta

from app.main import app
from app.core.auth import get_current_user
from app.db.session import get_db_session
from app.models.user import User
from app.services.report_service import ReportService, STATIC_REPORTS_DIR

client = TestClient(app)


class TestReport:
    @pytest.fixture(autouse=True)
    def setup_overrides(self):
        # Bypass database session context and auth constraints during testing
        app.dependency_overrides[get_db_session] = lambda: None
        mock_user = User(
            id="usr-mocked2",
            username="mockanalyst2",
            email="analyst2@chronoshield.ai",
            role="ANALYST",
            is_active=True,
        )
        app.dependency_overrides[get_current_user] = lambda: mock_user
        yield
        if get_current_user in app.dependency_overrides:
            del app.dependency_overrides[get_current_user]
        if get_db_session in app.dependency_overrides:
            del app.dependency_overrides[get_db_session]

    @pytest.mark.anyio
    async def test_generate_executive_report_success(self):
        """Verify report creation generates CSV & PDF files with summary stats."""
        now = datetime.utcnow()
        start = now - timedelta(days=1)

        # Trigger generation using mock fallback path
        report = await ReportService.generate_executive_report(
            None, "DAILY", start, now
        )

        assert report.id is not None
        assert report.status == "READY"
        assert report.report_type == "DAILY"

        # Verify JSON summary populated
        summary = json_data = {}
        try:
            summary = json_data = json_data = json_data = json_data = json_data = {}
            summary = json_data = json_data = json_data = json_data = json_data = {}
            summary = json_data = json_data = json_data = json_data = json_data = {}
            summary = json_data = json_data = json_data = json_data = json_data = {}
            summary = json_data = json_data = json_data = json_data = json_data = {}
            summary = json_data = json_data = json_data = json_data = json_data = {}
            import json

            summary = json.loads(report.summary)
        except Exception:
            pass

        assert "total_anomalies" in summary
        assert "system_health_avg" in summary

        # Verify files created in static directory
        csv_path = os.path.join(STATIC_REPORTS_DIR, f"{report.id}.csv")
        pdf_path = os.path.join(STATIC_REPORTS_DIR, f"{report.id}.pdf")

        assert os.path.exists(csv_path)
        assert os.path.exists(pdf_path)

        # Clean up files
        try:
            os.remove(csv_path)
            os.remove(pdf_path)
            html_path = pdf_path.replace(".pdf", ".html")
            if os.path.exists(html_path):
                os.remove(html_path)
        except Exception:
            pass

    def test_list_reports_api(self):
        """Verify list reports route yields list structure."""
        response = client.get("/api/v1/reports")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)

    def test_generate_report_api_validation(self):
        """Verify report request throws 400 bad request if start date is after end date."""
        payload = {
            "report_type": "DAILY",
            "start_date": datetime.utcnow().isoformat(),
            "end_date": (datetime.utcnow() - timedelta(hours=5)).isoformat(),
        }
        response = client.post("/api/v1/reports/generate", json=payload)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert (
            "Start date must be strictly before end date" in response.json()["detail"]
        )

    def test_generate_report_api_success(self):
        """Verify reports can be generated successfully via REST calls."""
        payload = {
            "report_type": "DAILY",
            "start_date": (datetime.utcnow() - timedelta(days=1)).isoformat(),
            "end_date": datetime.utcnow().isoformat(),
        }
        response = client.post("/api/v1/reports/generate", json=payload)
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["status"] == "READY"
        assert data["report_type"] == "DAILY"

        # Clean up generated files
        rep_id = data["id"]
        csv_path = os.path.join(STATIC_REPORTS_DIR, f"{rep_id}.csv")
        pdf_path = os.path.join(STATIC_REPORTS_DIR, f"{rep_id}.pdf")
        try:
            if os.path.exists(csv_path):
                os.remove(csv_path)
            if os.path.exists(pdf_path):
                os.remove(pdf_path)
            html_path = pdf_path.replace(".pdf", ".html")
            if os.path.exists(html_path):
                os.remove(html_path)
        except Exception:
            pass
