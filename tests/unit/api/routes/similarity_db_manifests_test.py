"""Tests for similarity_db_manifests admin routes."""

from unittest.mock import ANY, AsyncMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from graal.api.main import app


@pytest.fixture(autouse=True)
def mock_logging_config(mocker):
    """Avoid loading real logging.conf in tests."""

    mocker.patch("logging.config.fileConfig")


@pytest.fixture
def client() -> TestClient:
    """FastAPI test client."""

    return TestClient(app)


@pytest.fixture
def mock_admin_session_cookie() -> dict[str, str]:
    """Return headers with a fake admin session cookie."""

    return {"Cookie": "session=fake-admin-session"}


@pytest.fixture
def mock_auth_service():
    """Mock authorization service to always authorize as admin."""

    admin_user = type(
        "User",
        (),
        {"user_id": "00000000-0000-0000-0000-000000000000", "is_admin": True},
    )()

    mock_service = AsyncMock()
    # Used by CurrentUser dependency
    mock_service.get_current_user = AsyncMock(return_value=admin_user)
    # Used by require_admin / AdminUser dependency
    mock_service.require_admin = AsyncMock(return_value=admin_user)

    # Patch the authorization service factory in the auth dependencies module
    with patch(
        "graal.api.dependencies.auth.get_authorization_service",
        return_value=mock_service,
    ):
        yield mock_service


@pytest.fixture
def mock_manifest_service():
    """Mock SimilarityDBManifestService used by the routes."""

    mock_service = AsyncMock()
    mock_service.delete_database_by_id = AsyncMock()

    with patch(
        "graal.api.routes.similarity_db_manifests.get_similarity_db_manifest_service",
        return_value=mock_service,
    ):
        yield mock_service


class TestDeleteManifestWithFileRoute:
    """Tests for DELETE /admin/similarity-databases/{id}/with-file."""

    @pytest.mark.usefixtures("mock_auth_service")
    def test_deletes_database_and_manifest_via_id(
        self,
        client: TestClient,
        mock_manifest_service,
        mock_admin_session_cookie: dict[str, str],
    ) -> None:
        """Happy path: calls service with correct arguments and returns 204."""

        manifest_id = "11111111-1111-1111-1111-111111111111"

        response = client.delete(
            f"/api/v1/admin/similarity-databases/{manifest_id}/with-file",
            headers=mock_admin_session_cookie,
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT
        mock_manifest_service.delete_database_by_id.assert_awaited_once_with(ANY)
