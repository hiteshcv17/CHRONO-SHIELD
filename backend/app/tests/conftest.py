import pytest
from app.main import app
from app.core.auth import get_current_user
from app.models.user import User


@pytest.fixture(autouse=True)
def override_auth_for_tests():
    """
    Automatically override the get_current_user dependency for all tests
    to prevent breaking existing telemetry tests.
    """
    app.dependency_overrides[get_current_user] = lambda: User(
        id="usr-testadmin", username="admin", role="ADMIN", is_active=True
    )
    yield
    app.dependency_overrides.clear()
