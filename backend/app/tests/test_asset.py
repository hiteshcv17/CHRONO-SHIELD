import pytest
from fastapi import status
from fastapi.testclient import TestClient
from datetime import datetime

from app.main import app
from app.core.auth import get_current_user
from app.db.session import get_db_session
from app.models.user import User
from app.services.asset_service import AssetService

client = TestClient(app)

class TestAssetAPI:
    @pytest.fixture(autouse=True)
    def setup_overrides(self):
        # Override db session dependency to bypass active SQLite sessions
        app.dependency_overrides[get_db_session] = lambda: None
        # Default mock user as Analyst (has CRUD minus DELETE)
        self.mock_user = User(
            id="usr-analyst1",
            username="mockanalyst1",
            email="analyst1@chronoshield.ai",
            role="ANALYST",
            is_active=True
        )
        app.dependency_overrides[get_current_user] = lambda: self.mock_user
        yield
        if get_current_user in app.dependency_overrides:
            del app.dependency_overrides[get_current_user]
        if get_db_session in app.dependency_overrides:
            del app.dependency_overrides[get_db_session]

    def test_list_assets_api(self):
        """Verify listing assets works for authorized users."""
        response = client.get("/api/v1/assets")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert any(x["asset_type"] == "TRANSFORMER" for x in data)

    def test_get_asset_by_id_api(self):
        """Verify fetching single asset details."""
        # Query first to get an active ID
        list_response = client.get("/api/v1/assets")
        assets = list_response.json()
        target_id = assets[0]["id"]

        response = client.get(f"/api/v1/assets/{target_id}")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["id"] == target_id

    def test_create_asset_api(self):
        """Verify registration of new assets."""
        payload = {
            "name": "East Grid Transformer T-202",
            "asset_type": "TRANSFORMER",
            "status": "NOMINAL",
            "region": "East Sector",
            "dynamic_metadata": {"capacity_kva": 1500, "phase": 3}
        }
        response = client.post("/api/v1/assets", json=payload)
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == "East Grid Transformer T-202"
        assert data["dynamic_metadata"]["capacity_kva"] == 1500

    def test_update_asset_api(self):
        """Verify updating existing assets and their dynamic metadata."""
        list_response = client.get("/api/v1/assets")
        assets = list_response.json()
        target_id = assets[0]["id"]

        payload = {
            "name": "Updated Asset Name",
            "status": "MAINTENANCE",
            "dynamic_metadata": {"repaired": True, "notes": "annual inspection completed"}
        }
        response = client.put(f"/api/v1/assets/{target_id}", json=payload)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "Updated Asset Name"
        assert data["status"] == "MAINTENANCE"
        assert data["dynamic_metadata"]["repaired"] is True

    def test_delete_asset_api_denied_for_analyst(self):
        """Verify Analyst role is blocked from decommissioning (deleting) assets."""
        list_response = client.get("/api/v1/assets")
        assets = list_response.json()
        target_id = assets[0]["id"]

        response = client.delete(f"/api/v1/assets/{target_id}")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_delete_asset_api_success_for_admin(self):
        """Verify Admin role can decommission assets."""
        # Set user as Admin
        admin_user = User(
            id="usr-admin1",
            username="mockadmin1",
            email="admin1@chronoshield.ai",
            role="ADMIN",
            is_active=True
        )
        app.dependency_overrides[get_current_user] = lambda: admin_user

        list_response = client.get("/api/v1/assets")
        assets = list_response.json()
        target_id = assets[0]["id"]

        response = client.delete(f"/api/v1/assets/{target_id}")
        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_viewer_role_blocks_writes(self):
        """Verify Viewer role can read but cannot perform creation/update/deletions."""
        viewer_user = User(
            id="usr-viewer1",
            username="mockviewer1",
            email="viewer1@chronoshield.ai",
            role="VIEWER",
            is_active=True
        )
        app.dependency_overrides[get_current_user] = lambda: viewer_user

        # Read works
        assert client.get("/api/v1/assets").status_code == status.HTTP_200_OK

        # Writes fail
        payload = {
            "name": "Viewer Post Test",
            "asset_type": "PUBLIC_SYSTEM",
            "region": "Central Hub"
        }
        assert client.post("/api/v1/assets", json=payload).status_code == status.HTTP_403_FORBIDDEN
        assert client.put("/api/v1/assets/ast-tf01", json=payload).status_code == status.HTTP_403_FORBIDDEN
        assert client.delete("/api/v1/assets/ast-tf01").status_code == status.HTTP_403_FORBIDDEN
