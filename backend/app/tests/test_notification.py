import json
import pytest
from fastapi import status
from fastapi.testclient import TestClient
from datetime import datetime

from app.main import app
from app.core.auth import get_current_user
from app.db.session import get_db_session
from app.models.user import User
from app.models.alert import PrioritizedAlertRecord
from app.services.notification_service import NotificationDeliveryService

client = TestClient(app)


class TestNotification:
    @pytest.fixture(autouse=True)
    def setup_overrides(self):
        # Override DB session and authentication to bypass real DB dependencies
        app.dependency_overrides[get_db_session] = lambda: None
        # Mock operator with ANALYST role
        mock_user = User(
            id="usr-mocked1",
            username="mockanalyst",
            email="analyst@chronoshield.ai",
            role="ANALYST",
            is_active=True
        )
        app.dependency_overrides[get_current_user] = lambda: mock_user
        yield
        if get_current_user in app.dependency_overrides:
            del app.dependency_overrides[get_current_user]
        if get_db_session in app.dependency_overrides:
            del app.dependency_overrides[get_db_session]

    def test_template_rendering(self):
        """Verify that templates render with correct formats."""
        mock_alert = PrioritizedAlertRecord(
            id="alert-test-01",
            anomaly_id="anom-01",
            metric_name="CPU_Usage",
            original_severity="HIGH",
            current_severity="CRITICAL",
            priority_score=92.5,
            status="ACTIVE",
            occurrence_count=5,
            timestamp=datetime.utcnow(),
            last_occurrence=datetime.utcnow(),
            description="CPU load spiked beyond normal margins."
        )

        # Active state template
        title, msg = NotificationDeliveryService.render_template("ACTIVE", mock_alert)
        assert "NEW ALERT: CPU_Usage (CRITICAL)" in title
        assert "NEW ANOMALY DETECTED" in msg
        assert "92.5" in msg

        # Escalated state template
        title, msg = NotificationDeliveryService.render_template("ESCALATED", mock_alert)
        assert "SLA BREACH & ESCALATION" in title
        assert "SLA VIOLATION DECLARED" in msg

        # Resolved state template
        title, msg = NotificationDeliveryService.render_template("RESOLVED", mock_alert)
        assert "RESOLVED: Anomaly on CPU_Usage" in title
        assert "Resolution Report" in msg

    @pytest.mark.anyio
    async def test_trigger_notifications_skips_suppressed(self):
        """Verify suppressed alerts generate no notification dispatches."""
        mock_alert = PrioritizedAlertRecord(
            id="alert-test-02",
            anomaly_id="anom-02",
            metric_name="CPU_Usage",
            original_severity="LOW",
            current_severity="LOW",
            priority_score=15.0,
            status="SUPPRESSED",
            occurrence_count=1,
            timestamp=datetime.utcnow(),
            last_occurrence=datetime.utcnow(),
            description="Suppressed alert."
        )
        from app.services.notification_service import _MOCK_LOGS_REGISTRY
        initial_count = len(_MOCK_LOGS_REGISTRY)
        await NotificationDeliveryService.trigger_notifications(None, mock_alert)
        assert len(_MOCK_LOGS_REGISTRY) == initial_count

    def test_get_channels_api(self):
        """Test GET /api/v1/notifications/channels returns seeded channels."""
        response = client.get("/api/v1/notifications/channels")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) >= 3
        channel_types = [c["channel_type"] for c in data]
        assert "EMAIL" in channel_types
        assert "TELEGRAM" in channel_types
        assert "WEBHOOK" in channel_types

    def test_update_channel_api(self):
        """Test PUT /api/v1/notifications/channels/{channel_type} updates state."""
        # 1. Update EMAIL configuration
        new_config = {
            "recipient_email": "updated-email@chronoshield.ai",
            "smtp_host": "127.0.0.1",
            "smtp_port": 1025,
            "allowed_severities": ["HIGH", "CRITICAL"]
        }
        response = client.put(
            "/api/v1/notifications/channels/EMAIL",
            json={"config": json.dumps(new_config), "enabled": True}
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["enabled"] is True
        assert "updated-email@chronoshield.ai" in data["config"]

        # 2. Get channels again to verify persistence in mock store
        resp_check = client.get("/api/v1/notifications/channels")
        email_cfg = [c for c in resp_check.json() if c["channel_type"] == "EMAIL"][0]
        assert email_cfg["enabled"] is True
        assert "updated-email@chronoshield.ai" in email_cfg["config"]

    def test_test_dispatch_api(self):
        """Test POST /api/v1/notifications/channels/{channel_type}/test schedules mock delivery."""
        payload = {
            "channel": "EMAIL",
            "recipient": "test-recipient@chronoshield.ai",
            "message": "Verify notification pipeline connectivity."
        }
        response = client.post("/api/v1/notifications/channels/EMAIL/test", json=payload)
        assert response.status_code == status.HTTP_202_ACCEPTED
        data = response.json()
        assert data["status"] == "PENDING"
        assert data["recipient"] == "test-recipient@chronoshield.ai"
        assert data["channel"] == "EMAIL"

    def test_get_logs_api(self):
        """Test GET /api/v1/notifications/logs retrieves log logs queues."""
        # Insert a mock log directly
        from app.services.notification_service import _MOCK_LOGS_REGISTRY
        from app.models.notification import NotificationDeliveryLog
        
        test_log = NotificationDeliveryLog(
            id="log-unit-test-1",
            channel="WEBHOOK",
            recipient="http://localhost:8000/api/v1/notifications/webhook-test",
            title="Webhook test title",
            message="Webhook test body",
            priority="MEDIUM",
            status="SENT",
            retry_count=0,
            max_retries=3,
            timestamp=datetime.utcnow()
        )
        _MOCK_LOGS_REGISTRY.insert(0, test_log)

        response = client.get("/api/v1/notifications/logs")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) >= 1
        assert data[0]["id"] == "log-unit-test-1"
        assert data[0]["channel"] == "WEBHOOK"
        assert data[0]["status"] == "SENT"
