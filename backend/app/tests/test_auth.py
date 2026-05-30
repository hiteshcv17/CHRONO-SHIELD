import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi import status
from fastapi.testclient import TestClient

from app.main import app
from app.core.security import get_password_hash, verify_password, create_access_token, create_refresh_token, decode_token
from app.core.auth import get_current_user, require_admin
from app.db.session import get_db_session, get_redis_client
from app.models.user import User

client = TestClient(app)


def test_password_hashing():
    """Verify password hashing and validation."""
    password = "supersecretpassword"
    hashed = get_password_hash(password)
    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("wrongpassword", hashed) is False


def test_token_creation_and_decoding():
    """Verify JWT token creation and verification flow."""
    username = "testuser"
    access_token = create_access_token(username)
    refresh_token = create_refresh_token(username)

    decoded_access = decode_token(access_token)
    assert decoded_access.get("sub") == username
    assert decoded_access.get("type") == "access"

    decoded_refresh = decode_token(refresh_token)
    assert decoded_refresh.get("sub") == username
    assert decoded_refresh.get("type") == "refresh"
    assert "jti" in decoded_refresh


class TestAuthAPIEndpoints:

    @pytest.fixture(autouse=True)
    def setup_mocks(self):
        """Set up mock DB and Redis dependency overrides."""
        # Reset get_current_user override for our auth endpoint tests
        if get_current_user in app.dependency_overrides:
            del app.dependency_overrides[get_current_user]

        self.mock_db = AsyncMock()
        self.mock_redis = AsyncMock()

        app.dependency_overrides[get_db_session] = lambda: self.mock_db
        app.dependency_overrides[get_redis_client] = lambda: self.mock_redis
        app.dependency_overrides[require_admin] = lambda: None

        yield

        # Cleanup overrides
        if get_db_session in app.dependency_overrides:
            del app.dependency_overrides[get_db_session]
        if get_redis_client in app.dependency_overrides:
            del app.dependency_overrides[get_redis_client]
        if require_admin in app.dependency_overrides:
            del app.dependency_overrides[require_admin]

    def test_register_user_success(self):
        """Test successful registration endpoint."""
        # Mock database execute returning None (username and email are free)
        from datetime import datetime
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        self.mock_db.execute.return_value = mock_result

        async def mock_refresh(user):
            user.id = "usr-mockuser1"
            user.created_at = datetime.utcnow()
        self.mock_db.refresh.side_effect = mock_refresh

        response = client.post(
            "/api/v1/auth/register",
            json={"username": "newuser", "password": "securepassword", "email": "new@chronoshield.ai"}
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["username"] == "newuser"
        assert data["email"] == "new@chronoshield.ai"
        assert "id" in data
        assert data["is_active"] is True

    def test_register_username_taken(self):
        """Test registration when username already exists."""
        # Mock database execute returning an existing user
        existing_user = User(username="newuser", hashed_password="hashed", role="VIEWER")
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_user
        self.mock_db.execute.return_value = mock_result

        response = client.post(
            "/api/v1/auth/register",
            json={"username": "newuser", "password": "securepassword", "email": "new@chronoshield.ai"}
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "already taken" in response.json()["error"]["message"]

    def test_login_success(self):
        """Test successful login returns access token and sets cookie."""
        # Mock user retrieval
        hashed_pwd = get_password_hash("mypw123")
        user = User(username="loginuser", hashed_password=hashed_pwd, role="VIEWER", is_active=True)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = user
        self.mock_db.execute.return_value = mock_result

        response = client.post(
            "/api/v1/auth/login",
            json={"username": "loginuser", "password": "mypw123"}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "refresh_token" in response.cookies

    def test_login_invalid_credentials(self):
        """Test login with wrong password."""
        # Mock user retrieval
        hashed_pwd = get_password_hash("mypw123")
        user = User(username="loginuser", hashed_password=hashed_pwd, role="VIEWER", is_active=True)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = user
        self.mock_db.execute.return_value = mock_result

        response = client.post(
            "/api/v1/auth/login",
            json={"username": "loginuser", "password": "wrongpassword"}
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Incorrect username or password" in response.json()["detail"]

    def test_logout(self):
        """Test logout clears the cookie and removes refresh token from redis."""
        # Generate token
        refresh_token = create_refresh_token("someuser")
        response = client.post(
            "/api/v1/auth/logout",
            cookies={"refresh_token": refresh_token}
        )

        assert response.status_code == status.HTTP_200_OK
        # The cookie should be deleted (value set to empty or past expiry)
        assert response.cookies.get("refresh_token") is None or response.cookies.get("refresh_token") == ""
        # Redis delete should have been called
        self.mock_redis.delete.assert_called_once()

    def test_get_me_endpoint(self):
        """Test protected /me endpoint with correct access token."""
        # Mock get_current_user to return mock user
        from datetime import datetime
        mock_user = User(
            id="usr-mockid12",
            username="curruser",
            email="curr@chronoshield.ai",
            role="VIEWER",
            is_active=True,
            created_at=datetime.utcnow()
        )
        
        # Override dependency get_current_user
        app.dependency_overrides[get_current_user] = lambda: mock_user

        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer fake-token"}
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["username"] == "curruser"
        assert response.json()["email"] == "curr@chronoshield.ai"
