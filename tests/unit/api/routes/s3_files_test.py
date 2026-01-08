"""Unit tests for S3 admin routes.

These tests focus on the behavior of deleting similarity database files via
`DELETE /admin/s3/databases/{database_name}` and its interaction with
similarity DB manifests.
"""

from collections.abc import Iterator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from graal.api.main import app


@pytest.fixture(autouse=True)
def mock_logging_config(mocker):
    """Avoid loading real logging.conf in tests."""

    mocker.patch("logging.config.fileConfig")


@pytest.fixture
def client() -> Iterator[TestClient]:
    """FastAPI test client."""

    with TestClient(app) as client:
        yield client


@pytest.fixture
def mock_admin_session_cookie():
    """Return headers with a fake admin session cookie.

    The authorization service is mocked to treat any session as admin, so the
    concrete value does not matter here.
    """

    return {"Cookie": "session=fake-admin-session"}


@pytest.fixture
def mock_s3_service(mocker):
    """Mock S3Service used by the routes."""

    mock_db_service = AsyncMock()
    mock_db_service.delete_database_file = AsyncMock()

    mock_s3 = MagicMock()
    mock_s3.database = mock_db_service
    mock_s3.similarity_db_folder = "similarity_dbs"

    with patch("graal.api.routes.s3_files.get_s3_service", return_value=mock_s3):
        yield mock_s3
