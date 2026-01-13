"""Tests for database builder permission enforcement (writer role)."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from graal.api.main import app
from graal.api.services.database_permission_service import DbRole
from graal.database.enums import DbRoleEnum


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
def mock_session_cookie() -> dict[str, str]:
    return {"Cookie": "session=fake-session"}


def _make_manifest(manifest_id: str, name: str):
    # Minimal manifest interface for the routes under test
    return SimpleNamespace(
        id=manifest_id,
        name=name,
        size_bytes=123,
        last_modified=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
        input_files={"files": []},
    )


class TestAppendDatabasePermissions:
    """Tests for POST /api/v1/databases/{name}/append permission checks."""

    def _patch_auth_as_user(self, user_id: str, is_admin: bool):
        user = SimpleNamespace(user_id=user_id, is_admin=is_admin)
        mock_service = AsyncMock()
        mock_service.get_current_user = AsyncMock(return_value=user)
        mock_service.require_admin = AsyncMock(return_value=user)
        return patch(
            "graal.api.dependencies.auth.get_authorization_service",
            return_value=mock_service,
        )

    @pytest.mark.usefixtures("mock_logging_config")
    def test_append_forbidden_for_reader(self, client: TestClient, mock_session_cookie):
        manifest = _make_manifest(
            "11111111-1111-1111-1111-111111111111",
            "DB1",
        )

        mock_manifest_service = AsyncMock()
        mock_manifest_service.list_active_manifests = AsyncMock(return_value=[manifest])

        mock_perm_service = AsyncMock()
        mock_perm_service.get_user_role = AsyncMock(return_value=DbRoleEnum.reader)

        with (
            self._patch_auth_as_user(
                user_id="00000000-0000-0000-0000-000000000001",
                is_admin=False,
            ),
            patch(
                "graal.api.routes.database_builder.get_similarity_db_manifest_service",
                return_value=mock_manifest_service,
            ),
            patch(
                "graal.api.routes.database_builder.get_database_permission_service",
                return_value=mock_perm_service,
            ),
        ):
            response = client.post(
                "/api/v1/databases/DB1/append",
                headers=mock_session_cookie,
                json={
                    "config_file": "Fichier de configuration GRAAL - DSS - latest.xlsx",
                    "file_references": [
                        {
                            "upload_id": "hash1",
                            "filename": "file.json",
                            "file_hash": "hash1",
                            "s3_key": "pool/hash1-file.json",
                            "metadata": {
                                "default_processing_timestamp": 1700000000,
                                "origin_project": "PLFSS 2024",
                            },
                        }
                    ],
                },
            )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.usefixtures("mock_logging_config")
    def test_append_allowed_for_writer(self, client: TestClient, mock_session_cookie):
        manifest = _make_manifest(
            "11111111-1111-1111-1111-111111111111",
            "DB1",
        )

        mock_manifest_service = AsyncMock()
        mock_manifest_service.list_active_manifests = AsyncMock(return_value=[manifest])

        mock_perm_service = AsyncMock()
        mock_perm_service.get_user_role = AsyncMock(return_value=DbRole.writer)

        class DummyJobRegistry:
            def create_job(self, *args, **kwargs):
                return None

        class DummyBuilderService:
            def __init__(self):
                self.job_registry = DummyJobRegistry()

            async def start_database_build(self, *args, **kwargs):
                return None

        class DummyPool:
            async def download_from_input_pool(self, _s3_key: str) -> bytes:
                return b"dummy"

        class DummyS3Service:
            def __init__(self):
                self.pool = DummyPool()

        with (
            self._patch_auth_as_user(
                user_id="00000000-0000-0000-0000-000000000001",
                is_admin=False,
            ),
            patch(
                "graal.api.routes.database_builder.get_similarity_db_manifest_service",
                return_value=mock_manifest_service,
            ),
            patch(
                "graal.api.routes.database_builder.get_database_permission_service",
                return_value=mock_perm_service,
            ),
            patch(
                "graal.api.routes.database_builder.get_database_builder_service",
                return_value=DummyBuilderService(),
            ),
            patch(
                "graal.api.routes.database_builder.get_s3_service",
                return_value=DummyS3Service(),
            ),
        ):
            response = client.post(
                "/api/v1/databases/DB1/append",
                headers=mock_session_cookie,
                json={
                    "config_file": "Fichier de configuration GRAAL - DSS - latest.xlsx",
                    "file_references": [
                        {
                            "upload_id": "hash1",
                            "filename": "file.json",
                            "file_hash": "hash1",
                            "s3_key": "pool/hash1-file.json",
                            "metadata": {
                                "default_processing_timestamp": 1700000000,
                                "origin_project": "PLFSS 2024",
                            },
                        }
                    ],
                },
            )

        assert response.status_code == status.HTTP_200_OK
        payload = response.json()
        assert "job_id" in payload

    @pytest.mark.usefixtures("mock_logging_config")
    def test_append_unknown_database_returns_404(
        self, client: TestClient, mock_session_cookie
    ):
        mock_manifest_service = AsyncMock()
        mock_manifest_service.list_active_manifests = AsyncMock(return_value=[])

        mock_perm_service = AsyncMock()
        mock_perm_service.get_user_role = AsyncMock(return_value=DbRoleEnum.writer)

        with (
            self._patch_auth_as_user(
                user_id="00000000-0000-0000-0000-000000000001",
                is_admin=False,
            ),
            patch(
                "graal.api.routes.database_builder.get_similarity_db_manifest_service",
                return_value=mock_manifest_service,
            ),
            patch(
                "graal.api.routes.database_builder.get_database_permission_service",
                return_value=mock_perm_service,
            ),
        ):
            response = client.post(
                "/api/v1/databases/UNKNOWN_DB/append",
                headers=mock_session_cookie,
                json={
                    "config_file": "Fichier de configuration GRAAL - DSS - latest.xlsx",
                    "file_references": [
                        {
                            "upload_id": "hash1",
                            "filename": "file.json",
                            "file_hash": "hash1",
                            "s3_key": "pool/hash1-file.json",
                            "metadata": {
                                "default_processing_timestamp": 1700000000,
                                "origin_project": "PLFSS 2024",
                            },
                        }
                    ],
                },
            )

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestAppendableDatabases:
    """Tests for GET /api/v1/databases/appendable."""

    def _patch_auth_as_user(self, user_id: str, is_admin: bool):
        user = SimpleNamespace(user_id=user_id, is_admin=is_admin)
        mock_service = AsyncMock()
        mock_service.get_current_user = AsyncMock(return_value=user)
        mock_service.require_admin = AsyncMock(return_value=user)
        return patch(
            "graal.api.dependencies.auth.get_authorization_service",
            return_value=mock_service,
        )

    @pytest.mark.usefixtures("mock_logging_config")
    def test_lists_only_writer_owner_for_non_admin(
        self, client: TestClient, mock_session_cookie
    ):
        db1 = _make_manifest("11111111-1111-1111-1111-111111111111", "DB1")
        db2 = _make_manifest("22222222-2222-2222-2222-222222222222", "DB2")

        mock_manifest_service = AsyncMock()
        mock_manifest_service.list_active_manifests = AsyncMock(return_value=[db1, db2])

        mock_perm_service = AsyncMock()
        mock_perm_service.list_databases_for_user_with_roles = AsyncMock(
            return_value=[str(db2.id)]
        )

        with (
            self._patch_auth_as_user(
                user_id="00000000-0000-0000-0000-000000000001",
                is_admin=False,
            ),
            patch(
                "graal.api.routes.database_builder.get_similarity_db_manifest_service",
                return_value=mock_manifest_service,
            ),
            patch(
                "graal.api.routes.database_builder.get_database_permission_service",
                return_value=mock_perm_service,
            ),
        ):
            response = client.get(
                "/api/v1/databases/appendable",
                headers=mock_session_cookie,
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert [db["name"] for db in data["databases"]] == ["DB2"]

    @pytest.mark.usefixtures("mock_logging_config")
    def test_appendable_lists_all_for_admin(
        self, client: TestClient, mock_session_cookie
    ):
        db1 = _make_manifest("11111111-1111-1111-1111-111111111111", "DB1")
        db2 = _make_manifest("22222222-2222-2222-2222-222222222222", "DB2")

        mock_manifest_service = AsyncMock()
        mock_manifest_service.list_active_manifests = AsyncMock(return_value=[db1, db2])

        mock_perm_service = AsyncMock()
        mock_perm_service.list_databases_for_user_with_roles = AsyncMock(
            return_value=[]
        )

        with (
            self._patch_auth_as_user(
                user_id="00000000-0000-0000-0000-000000000001",
                is_admin=True,
            ),
            patch(
                "graal.api.routes.database_builder.get_similarity_db_manifest_service",
                return_value=mock_manifest_service,
            ),
            patch(
                "graal.api.routes.database_builder.get_database_permission_service",
                return_value=mock_perm_service,
            ),
        ):
            response = client.get(
                "/api/v1/databases/appendable",
                headers=mock_session_cookie,
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert [db["name"] for db in data["databases"]] == ["DB1", "DB2"]
        mock_perm_service.list_databases_for_user_with_roles.assert_not_awaited()


class TestDatabaseManifestPermissions:
    """Tests for GET /api/v1/databases/{name}/manifest permission checks."""

    def _patch_auth_as_user(self, user_id: str, is_admin: bool):
        user = SimpleNamespace(user_id=user_id, is_admin=is_admin)
        mock_service = AsyncMock()
        mock_service.get_current_user = AsyncMock(return_value=user)
        mock_service.require_admin = AsyncMock(return_value=user)
        return patch(
            "graal.api.dependencies.auth.get_authorization_service",
            return_value=mock_service,
        )

    @pytest.mark.usefixtures("mock_logging_config")
    def test_manifest_forbidden_for_user_without_role(
        self, client: TestClient, mock_session_cookie
    ):
        manifest = _make_manifest(
            "11111111-1111-1111-1111-111111111111",
            "DB1",
        )

        mock_manifest_service = AsyncMock()
        mock_manifest_service.list_active_manifests = AsyncMock(return_value=[manifest])

        mock_perm_service = AsyncMock()
        mock_perm_service.get_user_role = AsyncMock(return_value=None)

        with (
            self._patch_auth_as_user(
                user_id="00000000-0000-0000-0000-000000000001",
                is_admin=False,
            ),
            patch(
                "graal.api.routes.database_builder.get_similarity_db_manifest_service",
                return_value=mock_manifest_service,
            ),
            patch(
                "graal.api.routes.database_builder.get_database_permission_service",
                return_value=mock_perm_service,
            ),
        ):
            response = client.get(
                "/api/v1/databases/DB1/manifest",
                headers=mock_session_cookie,
            )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.usefixtures("mock_logging_config")
    def test_manifest_allowed_for_reader(self, client: TestClient, mock_session_cookie):
        manifest = _make_manifest(
            "11111111-1111-1111-1111-111111111111",
            "DB1",
        )

        mock_manifest_service = AsyncMock()
        mock_manifest_service.list_active_manifests = AsyncMock(return_value=[manifest])

        mock_perm_service = AsyncMock()
        mock_perm_service.get_user_role = AsyncMock(return_value=DbRoleEnum.reader)

        with (
            self._patch_auth_as_user(
                user_id="00000000-0000-0000-0000-000000000001",
                is_admin=False,
            ),
            patch(
                "graal.api.routes.database_builder.get_similarity_db_manifest_service",
                return_value=mock_manifest_service,
            ),
            patch(
                "graal.api.routes.database_builder.get_database_permission_service",
                return_value=mock_perm_service,
            ),
        ):
            response = client.get(
                "/api/v1/databases/DB1/manifest",
                headers=mock_session_cookie,
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["database_name"] == "DB1"
        assert data["total_files"] == 0
