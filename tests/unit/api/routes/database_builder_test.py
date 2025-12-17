"""
Tests for database_builder route helper functions.
"""

from unittest.mock import AsyncMock, Mock

import pytest

from graal.api.routes.database_builder import (
    _download_file_to_temp,
)


class TestDownloadFileToTemp:
    """Test _download_file_to_temp async helper function."""

    @pytest.fixture
    def temp_dir(self, tmp_path):
        """Provide a temporary directory for tests."""
        return tmp_path / "test_uploads"

    @pytest.fixture
    def mock_s3_service(self):
        """Mock S3 service with download capability."""
        mock_service = Mock()
        mock_service.download_from_input_pool = AsyncMock()
        return mock_service

    @pytest.mark.asyncio
    async def test_downloads_file_when_not_present(self, mock_s3_service, temp_dir):
        """Test file is downloaded when it doesn't exist in temp directory."""
        # Arrange
        temp_dir.mkdir(parents=True, exist_ok=True)
        file_metadata = {
            "s3_key": "pool/abc/def/test.json",
            "upload_id": "hash123",
            "filename": "test.json",
        }
        file_content = b'{"test": "data"}'
        mock_s3_service.download_from_input_pool.return_value = file_content

        await _download_file_to_temp(mock_s3_service, file_metadata, temp_dir)

        # Assert
        mock_s3_service.download_from_input_pool.assert_called_once_with(
            "pool/abc/def/test.json"
        )

        # Verify file was written
        expected_path = temp_dir / "hash123_test.json"
        assert expected_path.exists()
        assert expected_path.read_bytes() == file_content

    @pytest.mark.asyncio
    async def test_skips_download_when_file_exists(self, mock_s3_service, temp_dir):
        """Test file download is skipped when file already exists."""
        # Arrange
        temp_dir.mkdir(parents=True, exist_ok=True)
        file_metadata = {
            "s3_key": "pool/xyz/uvw/existing.json",
            "upload_id": "hash456",
            "filename": "existing.json",
        }

        # Pre-create the file
        existing_path = temp_dir / "hash456_existing.json"
        existing_content = b"existing content"
        existing_path.write_bytes(existing_content)

        # Act
        await _download_file_to_temp(mock_s3_service, file_metadata, temp_dir)

        # Assert
        mock_s3_service.download_from_input_pool.assert_not_called()

        # Verify file content unchanged
        assert existing_path.read_bytes() == existing_content

    @pytest.mark.asyncio
    async def test_creates_file_with_correct_naming_pattern(
        self, mock_s3_service, temp_dir
    ):
        """Test downloaded file follows upload_id_filename pattern."""
        # Arrange
        temp_dir.mkdir(parents=True, exist_ok=True)
        file_metadata = {
            "s3_key": "pool/test/key.json",
            "upload_id": "unique_hash_789",
            "filename": "my_amendments.json",
        }
        mock_s3_service.download_from_input_pool.return_value = b"test data"

        # Act
        await _download_file_to_temp(mock_s3_service, file_metadata, temp_dir)

        # Assert
        expected_filename = "unique_hash_789_my_amendments.json"
        expected_path = temp_dir / expected_filename
        assert expected_path.exists()

    @pytest.mark.asyncio
    async def test_handles_s3_download_errors(self, mock_s3_service, temp_dir):
        """Test error handling when S3 download fails."""
        # Arrange
        temp_dir.mkdir(parents=True, exist_ok=True)
        file_metadata = {
            "s3_key": "pool/invalid/file.json",
            "upload_id": "hash_error",
            "filename": "error_file.json",
        }
        mock_s3_service.download_from_input_pool.side_effect = Exception(
            "S3 download failed"
        )

        # Act & Assert
        with pytest.raises(Exception, match="S3 download failed"):
            await _download_file_to_temp(mock_s3_service, file_metadata, temp_dir)

        # Verify file was not created
        expected_path = temp_dir / "hash_error_error_file.json"
        assert not expected_path.exists()

    @pytest.mark.asyncio
    async def test_downloads_multiple_files_sequentially(
        self, mock_s3_service, temp_dir
    ):
        """Test multiple files can be downloaded to the same directory."""
        # Arrange
        temp_dir.mkdir(parents=True, exist_ok=True)
        files = [
            {
                "s3_key": f"pool/test/file{i}.json",
                "upload_id": f"hash{i}",
                "filename": f"file{i}.json",
            }
            for i in range(3)
        ]
        mock_s3_service.download_from_input_pool.return_value = b"content"

        # Act
        for file_metadata in files:
            await _download_file_to_temp(mock_s3_service, file_metadata, temp_dir)

        # Assert
        assert mock_s3_service.download_from_input_pool.call_count == 3
        for i in range(3):
            expected_path = temp_dir / f"hash{i}_file{i}.json"
            assert expected_path.exists()
