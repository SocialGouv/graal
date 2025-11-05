"""
Tests for manifest service.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from graal.utils.manifest_service import (
    DatabaseManifest,
    InputFileReference,
    ManifestService,
)


class TestManifestService:
    """Test cases for ManifestService."""

    @pytest.fixture
    def mock_s3_service(self):
        """Create a mock S3Service."""
        mock = MagicMock()
        mock._bucket_name = "test-bucket"
        mock._s3_client = MagicMock()
        mock._s3_client._endpoint.host = "https://s3.test.com"
        mock._aioboto3_session = MagicMock()
        mock._s3_config = MagicMock()
        return mock

    @pytest.fixture
    def service(self, mock_s3_service):
        """Create a ManifestService with mocked S3Service."""
        with patch("graal.utils.manifest_service.get_s3_service") as mock_get_s3:
            mock_get_s3.return_value = mock_s3_service
            return ManifestService()

    @pytest.fixture
    def sample_input_file(self):
        """Create a sample InputFileReference."""
        return InputFileReference(
            s3_key="input_files/pool/abc123.json",
            file_hash="abc123",
            user_provided_filename="lecture.json",
            uploaded_at=datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc),
            metadata={"origin_project": "PLFSS 2024"},
        )

    @pytest.fixture
    def sample_manifest(self, sample_input_file):
        """Create a sample DatabaseManifest."""
        return DatabaseManifest(
            database_name="PLFSS_2024",
            created_at=datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc),
            last_updated_at=datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc),
            input_files=[sample_input_file],
            parquet_output="similarity_dbs/PLFSS_2024.parquet",
        )

    def test_serialize_manifest(self, service, sample_manifest):
        """Test manifest serialization to JSON-compatible dict."""
        manifest_dict = service._serialize_manifest(sample_manifest)

        assert manifest_dict["database_name"] == "PLFSS_2024"
        assert manifest_dict["created_at"] == "2024-01-15T10:30:00+00:00"
        assert manifest_dict["last_updated_at"] == "2024-01-15T10:30:00+00:00"
        assert len(manifest_dict["input_files"]) == 1
        assert (
            manifest_dict["input_files"][0]["s3_key"] == "input_files/pool/abc123.json"
        )
        assert manifest_dict["input_files"][0]["file_hash"] == "abc123"
        assert manifest_dict["parquet_output"] == "similarity_dbs/PLFSS_2024.parquet"

    def test_deserialize_manifest(self, service):
        """Test manifest deserialization from JSON dict."""
        manifest_dict = {
            "database_name": "PLFSS_2024",
            "created_at": "2024-01-15T10:30:00",
            "last_updated_at": "2024-01-15T10:30:00",
            "input_files": [
                {
                    "s3_key": "input_files/pool/abc123.json",
                    "file_hash": "abc123",
                    "user_provided_filename": "lecture.json",
                    "uploaded_at": "2024-01-15T10:30:00",
                    "metadata": {"origin_project": "PLFSS 2024"},
                }
            ],
            "parquet_output": "similarity_dbs/PLFSS_2024.parquet",
        }

        manifest = service._deserialize_manifest(manifest_dict)

        assert manifest.database_name == "PLFSS_2024"
        assert manifest.created_at == datetime(
            2024, 1, 15, 10, 30, 0
        )  # Naive from mock data
        assert len(manifest.input_files) == 1
        assert manifest.input_files[0].file_hash == "abc123"

    def test_deserialize_manifest_invalid_structure(self, service):
        """Test error handling for invalid manifest structure."""
        invalid_dict = {
            "database_name": "PLFSS_2024",
            # Missing required fields
        }

        with pytest.raises(ValueError, match="Invalid manifest structure"):
            service._deserialize_manifest(invalid_dict)

    def test_validate_manifest_valid(self, service, sample_manifest):
        """Test validation of valid manifest."""
        # Should not raise any exception
        service._validate_manifest(sample_manifest)

    def test_validate_manifest_empty_database_name(self, service, sample_manifest):
        """Test validation fails for empty database name."""
        sample_manifest.database_name = ""

        with pytest.raises(ValueError, match="database_name cannot be empty"):
            service._validate_manifest(sample_manifest)

    def test_validate_manifest_empty_parquet_output(self, service, sample_manifest):
        """Test validation fails for empty parquet output."""
        sample_manifest.parquet_output = ""

        with pytest.raises(ValueError, match="parquet_output cannot be empty"):
            service._validate_manifest(sample_manifest)

    def test_validate_manifest_empty_input_files(self, service, sample_manifest):
        """Test validation fails for empty input files list."""
        sample_manifest.input_files = []

        with pytest.raises(ValueError, match="input_files cannot be empty"):
            service._validate_manifest(sample_manifest)

    def test_validate_manifest_invalid_file_reference(self, service, sample_manifest):
        """Test validation fails for invalid file reference."""
        sample_manifest.input_files[0].s3_key = ""

        with pytest.raises(
            ValueError, match="input_files\\[0\\].s3_key cannot be empty"
        ):
            service._validate_manifest(sample_manifest)

    def test_get_manifest_s3_key(self, service):
        """Test S3 key generation for manifest."""
        s3_key = service._get_manifest_s3_key("PLFSS_2024")
        assert s3_key == "input_files/manifests/PLFSS_2024.json"

    @pytest.mark.asyncio
    async def test_load_manifest(self, service):
        """Test loading manifest from S3."""
        manifest_dict = {
            "database_name": "PLFSS_2024",
            "created_at": "2024-01-15T10:30:00",
            "last_updated_at": "2024-01-15T10:30:00",
            "input_files": [
                {
                    "s3_key": "input_files/pool/abc123.json",
                    "file_hash": "abc123",
                    "user_provided_filename": "lecture.json",
                    "uploaded_at": "2024-01-15T10:30:00",
                    "metadata": {},
                }
            ],
            "parquet_output": "similarity_dbs/PLFSS_2024.parquet",
        }

        with patch.object(
            service, "_download_manifest_from_s3", new_callable=AsyncMock
        ) as mock_download:
            mock_download.return_value = manifest_dict

            manifest = await service.load_manifest("PLFSS_2024")

            assert manifest.database_name == "PLFSS_2024"
            assert len(manifest.input_files) == 1
            mock_download.assert_called_once()

    @pytest.mark.asyncio
    async def test_load_manifest_not_found(self, service):
        """Test error handling when manifest doesn't exist."""
        with patch.object(
            service, "_download_manifest_from_s3", new_callable=AsyncMock
        ) as mock_download:
            mock_download.side_effect = FileNotFoundError("Manifest not found")

            with pytest.raises(FileNotFoundError):
                await service.load_manifest("NonExistent")

    @pytest.mark.asyncio
    async def test_update_manifest(self, service, sample_input_file):
        """Test updating manifest with additional files."""
        existing_manifest_dict = {
            "database_name": "PLFSS_2024",
            "created_at": "2024-01-15T10:30:00+00:00",
            "last_updated_at": "2024-01-15T10:30:00+00:00",
            "input_files": [
                {
                    "s3_key": "input_files/pool/abc123.json",
                    "file_hash": "abc123",
                    "user_provided_filename": "lecture1.json",
                    "uploaded_at": "2024-01-15T10:30:00+00:00",
                    "metadata": {},
                }
            ],
            "parquet_output": "similarity_dbs/PLFSS_2024.parquet",
        }

        new_file = InputFileReference(
            s3_key="input_files/pool/def456.json",
            file_hash="def456",
            user_provided_filename="lecture2.json",
            uploaded_at=datetime(2024, 1, 20, 14, 0, 0, tzinfo=timezone.utc),
            metadata={},
        )

        with (
            patch.object(
                service, "_download_manifest_from_s3", new_callable=AsyncMock
            ) as mock_download,
            patch.object(
                service, "_upload_manifest_to_s3", new_callable=AsyncMock
            ) as mock_upload,
        ):
            mock_download.return_value = existing_manifest_dict

            manifest = await service.update_manifest("PLFSS_2024", [new_file])

            # Verify manifest was updated
            assert len(manifest.input_files) == 2
            assert manifest.input_files[1].file_hash == "def456"
            assert manifest.last_updated_at > manifest.created_at

            # Verify S3 operations were called
            mock_download.assert_called_once()
            mock_upload.assert_called_once()
