"""
Tests for the S3Service new methods (input pool and manifest operations).

This module tests the newly added functionality for file reuse and append features.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from botocore.exceptions import ClientError

from graal.utils.s3_service import S3Service


class TestS3ServiceInputPool:
    """Test suite for S3Service input pool methods."""

    @pytest.fixture
    def s3_service(self, mocker):
        """Create a mock S3Service instance for testing."""
        # Mock environment variables
        mocker.patch.dict(
            "os.environ",
            {
                "S3_BUCKET_NAME": "test-bucket",
                "S3_BUCKET_ENDPOINT": "https://s3.test.com",
                "S3_BUCKET_ACCESS_KEY": "<test-access-key>",
                "S3_BUCKET_SECRET_KEY": "<test-secret-key>",
                "S3_CONFIG_FOLDER": "config",
                "S3_SIMILARITY_DB_FOLDER": "similarity_dbs",
                "S3_INPUT_POOL_FOLDER": "input_files/pool",
                "S3_MANIFEST_FOLDER": "input_files/manifests",
            },
        )

        # Mock boto3 client
        mock_boto3_client = MagicMock()
        mock_boto3_client.head_bucket = MagicMock()
        mocker.patch("boto3.client", return_value=mock_boto3_client)

        # Mock aioboto3 session
        mock_aioboto3_session = MagicMock()
        mocker.patch("aioboto3.Session", return_value=mock_aioboto3_session)

        service = S3Service()
        return service

    @pytest.mark.asyncio
    async def test_upload_to_input_pool_success(self, s3_service, mocker):
        """Test successful file upload to input pool."""
        # Mock async S3 client
        mock_s3_client = AsyncMock()
        mock_s3_client.put_object = AsyncMock()

        # Mock the context manager
        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_s3_client)
        mock_context.__aexit__ = AsyncMock()

        s3_service._aioboto3_session.client = MagicMock(return_value=mock_context)

        file_content = b"test file content"
        s3_key = "abc123.json"

        await s3_service.upload_to_input_pool(file_content, s3_key)

        # Verify put_object was called with correct parameters
        mock_s3_client.put_object.assert_called_once()
        call_kwargs = mock_s3_client.put_object.call_args[1]
        assert call_kwargs["Bucket"] == "test-bucket"
        assert call_kwargs["Key"] == "input_files/pool/abc123.json"
        assert call_kwargs["Body"] == file_content

    @pytest.mark.asyncio
    async def test_download_from_input_pool_success(self, s3_service, mocker):
        """Test successful file download from input pool."""
        # Mock response body
        mock_body = AsyncMock()
        mock_body.read = AsyncMock(return_value=b"test file content")

        # Mock async S3 client
        mock_s3_client = AsyncMock()
        mock_s3_client.get_object = AsyncMock(return_value={"Body": mock_body})

        # Mock the context manager
        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_s3_client)
        mock_context.__aexit__ = AsyncMock()

        s3_service._aioboto3_session.client = MagicMock(return_value=mock_context)

        s3_key = "abc123.json"
        result = await s3_service.download_from_input_pool(s3_key)

        assert result == b"test file content"
        mock_s3_client.get_object.assert_called_once()
        call_kwargs = mock_s3_client.get_object.call_args[1]
        assert call_kwargs["Bucket"] == "test-bucket"
        assert call_kwargs["Key"] == "input_files/pool/abc123.json"

    @pytest.mark.asyncio
    async def test_download_from_input_pool_not_found(self, s3_service, mocker):
        """Test file not found error when downloading from input pool."""
        # Create a proper ClientError
        error_response = {"Error": {"Code": "NoSuchKey"}}
        client_error = ClientError(error_response, "GetObject")

        # Mock async S3 client
        mock_s3_client = AsyncMock()
        mock_s3_client.get_object.side_effect = client_error

        # Mock the context manager properly
        async def mock_client_cm(*args, **kwargs):
            return mock_s3_client

        mock_context = MagicMock()
        mock_context.__aenter__ = AsyncMock(side_effect=mock_client_cm)
        mock_context.__aexit__ = AsyncMock(return_value=None)

        s3_service._aioboto3_session.client = MagicMock(return_value=mock_context)

        s3_key = "nonexistent.json"

        with pytest.raises(FileNotFoundError, match="File not found in input pool"):
            await s3_service.download_from_input_pool(s3_key)

    @pytest.mark.asyncio
    async def test_file_exists_in_pool_true(self, s3_service, mocker):
        """Test file exists check returns True."""
        # Mock async S3 client
        mock_s3_client = AsyncMock()
        mock_s3_client.head_object = AsyncMock()

        # Mock the context manager
        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_s3_client)
        mock_context.__aexit__ = AsyncMock()

        s3_service._aioboto3_session.client = MagicMock(return_value=mock_context)

        s3_key = "abc123.json"
        result = await s3_service.file_exists_in_pool(s3_key)

        assert result is True
        mock_s3_client.head_object.assert_called_once()

    @pytest.mark.asyncio
    async def test_file_exists_in_pool_false(self, s3_service, mocker):
        """Test file exists check returns False when file not found."""
        # Create a proper ClientError
        error_response = {"Error": {"Code": "404"}}
        client_error = ClientError(error_response, "HeadObject")

        # Mock async S3 client
        mock_s3_client = AsyncMock()
        mock_s3_client.head_object.side_effect = client_error

        # Mock the context manager properly
        async def mock_client_cm(*args, **kwargs):
            return mock_s3_client

        mock_context = MagicMock()
        mock_context.__aenter__ = AsyncMock(side_effect=mock_client_cm)
        mock_context.__aexit__ = AsyncMock(return_value=None)

        s3_service._aioboto3_session.client = MagicMock(return_value=mock_context)

        s3_key = "nonexistent.json"
        result = await s3_service.file_exists_in_pool(s3_key)

        assert result is False


class TestS3ServiceManifest:
    """Test suite for S3Service manifest methods."""

    @pytest.fixture
    def s3_service(self, mocker):
        """Create a mock S3Service instance for testing."""
        # Mock environment variables
        mocker.patch.dict(
            "os.environ",
            {
                "S3_BUCKET_NAME": "test-bucket",
                "S3_BUCKET_ENDPOINT": "https://s3.test.com",
                "S3_BUCKET_ACCESS_KEY": "<test-access-key>",
                "S3_BUCKET_SECRET_KEY": "<test-secret-key>",
                "S3_CONFIG_FOLDER": "config",
                "S3_SIMILARITY_DB_FOLDER": "similarity_dbs",
                "S3_INPUT_POOL_FOLDER": "input_files/pool",
                "S3_MANIFEST_FOLDER": "input_files/manifests",
            },
        )

        # Mock boto3 client
        mock_boto3_client = MagicMock()
        mock_boto3_client.head_bucket = MagicMock()
        mocker.patch("boto3.client", return_value=mock_boto3_client)

        # Mock aioboto3 session
        mock_aioboto3_session = MagicMock()
        mocker.patch("aioboto3.Session", return_value=mock_aioboto3_session)

        service = S3Service()
        return service
