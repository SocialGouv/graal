"""
Comprehensive tests for S3Service class.

This module tests all major S3Service operations including config files,
similarity databases, input pool, and manifest management.
"""

from datetime import datetime
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock

import pandas as pd
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

    @pytest.mark.asyncio
    async def test_upload_manifest_success(self, s3_service, mocker):
        """Test successful manifest upload."""
        # Mock async S3 client
        mock_s3_client = AsyncMock()
        mock_s3_client.put_object = AsyncMock()

        # Mock the context manager
        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_s3_client)
        mock_context.__aexit__ = AsyncMock()

        s3_service._aioboto3_session.client = MagicMock(return_value=mock_context)

        manifest_data = {"project": "PLFSS", "version": "2024", "files": ["file1.json"]}
        database_name = "PLFSS/2024"

        await s3_service.upload_manifest(database_name, manifest_data)

        # Verify put_object was called
        mock_s3_client.put_object.assert_called_once()
        call_kwargs = mock_s3_client.put_object.call_args[1]
        assert call_kwargs["Bucket"] == "test-bucket"
        assert call_kwargs["Key"] == "input_files/manifests/PLFSS/2024.json"
        assert call_kwargs["ContentType"] == "application/json"

    @pytest.mark.asyncio
    async def test_download_manifest_success(self, s3_service, mocker):
        """Test successful manifest download."""
        manifest_data = {"project": "PLFSS", "version": "2024"}
        manifest_json = '{"project": "PLFSS", "version": "2024"}'

        # Mock response body
        mock_body = AsyncMock()
        mock_body.read = AsyncMock(return_value=manifest_json.encode("utf-8"))

        # Mock async S3 client
        mock_s3_client = AsyncMock()
        mock_s3_client.get_object = AsyncMock(return_value={"Body": mock_body})

        # Mock the context manager
        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_s3_client)
        mock_context.__aexit__ = AsyncMock()

        s3_service._aioboto3_session.client = MagicMock(return_value=mock_context)

        result = await s3_service.download_manifest("PLFSS/2024")

        assert result == manifest_data
        mock_s3_client.get_object.assert_called_once()

    @pytest.mark.asyncio
    async def test_manifest_exists_true(self, s3_service, mocker):
        """Test manifest exists check returns True."""
        # Mock async S3 client
        mock_s3_client = AsyncMock()
        mock_s3_client.head_object = AsyncMock()

        # Mock the context manager
        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_s3_client)
        mock_context.__aexit__ = AsyncMock()

        s3_service._aioboto3_session.client = MagicMock(return_value=mock_context)

        result = await s3_service.manifest_exists("PLFSS/2024")

        assert result is True


class TestS3ServiceConfigOperations:
    """Test suite for S3Service config file operations (synchronous)."""

    @pytest.fixture
    def s3_service(self, mocker):
        """Create a mock S3Service instance for testing."""
        mocker.patch.dict(
            "os.environ",
            {
                "S3_BUCKET_NAME": "test-bucket",
                "S3_BUCKET_ENDPOINT": "https://s3.test.com",
                "S3_BUCKET_ACCESS_KEY": "test-key",
                "S3_BUCKET_SECRET_KEY": "test-secret",
                "S3_CONFIG_FOLDER": "config_graal",
                "S3_SIMILARITY_DB_FOLDER": "similarity_dbs",
            },
        )

        mock_boto3_client = MagicMock()
        mock_boto3_client.head_bucket = MagicMock()
        mocker.patch("boto3.client", return_value=mock_boto3_client)

        mock_aioboto3_session = MagicMock()
        mocker.patch("aioboto3.Session", return_value=mock_aioboto3_session)

        service = S3Service()
        service._s3_client = mock_boto3_client
        return service

    def test_list_available_config_files_success(self, s3_service):
        """Test listing config files returns sorted file names."""
        # Mock S3 list_objects_v2 response
        s3_service._s3_client.list_objects_v2.return_value = {
            "Contents": [
                {"Key": "config_graal/PLFSS_2024.xlsx"},
                {"Key": "config_graal/PLACSS_2023.xlsx"},
                {"Key": "config_graal/test_config.xlsx"},
            ]
        }

        result = s3_service.list_available_config_files()

        assert result == ["PLACSS_2023.xlsx", "PLFSS_2024.xlsx", "test_config.xlsx"]
        s3_service._s3_client.list_objects_v2.assert_called_once()

    def test_list_available_config_files_empty(self, s3_service):
        """Test listing config files when no files exist."""
        s3_service._s3_client.list_objects_v2.return_value = {}

        result = s3_service.list_available_config_files()

        assert result == []

    def test_list_available_config_files_filters_non_xlsx(self, s3_service):
        """Test that only .xlsx files are included."""
        s3_service._s3_client.list_objects_v2.return_value = {
            "Contents": [
                {"Key": "config_graal/PLFSS_2024.xlsx"},
                {"Key": "config_graal/README.md"},
                {"Key": "config_graal/data.csv"},
            ]
        }

        result = s3_service.list_available_config_files()

        assert result == ["PLFSS_2024.xlsx"]

    def test_validate_config_file_exists_true(self, s3_service):
        """Test config file existence check returns True."""
        s3_service._s3_client.head_object = MagicMock()

        result = s3_service.validate_config_file_exists("PLFSS_2024.xlsx")

        assert result is True
        s3_service._s3_client.head_object.assert_called_once()

    def test_validate_config_file_exists_false(self, s3_service):
        """Test config file existence check returns False when not found."""
        error_response = {"Error": {"Code": "404"}}
        s3_service._s3_client.head_object.side_effect = ClientError(
            error_response, "HeadObject"
        )

        result = s3_service.validate_config_file_exists("nonexistent.xlsx")

        assert result is False

    def test_load_config_excel_success(self, s3_service, mocker):
        """Test successful config file loading."""
        # Create mock Excel data
        mock_df = pd.DataFrame({"col1": [1, 2], "col2": ["a", "b"]})
        mock_excel_data = {"Sheet1": mock_df}

        # Mock download and read
        mock_file_content = BytesIO(b"mock excel content")
        s3_service._download_from_s3 = MagicMock(return_value=mock_file_content)
        mocker.patch("pandas.read_excel", return_value=mock_excel_data)

        result = s3_service.load_config_excel("test_config.xlsx")

        assert "Sheet1" in result
        assert isinstance(result["Sheet1"], pd.DataFrame)
        s3_service._download_from_s3.assert_called_once_with(
            "config_graal/test_config.xlsx"
        )

    def test_load_config_excel_not_found(self, s3_service):
        """Test loading non-existent config file raises FileNotFoundError."""
        s3_service._download_from_s3 = MagicMock(
            side_effect=FileNotFoundError("File not found")
        )

        with pytest.raises(FileNotFoundError):
            s3_service.load_config_excel("nonexistent.xlsx")

    def test_delete_config_file_success(self, s3_service):
        """Test successful config file deletion."""
        s3_service.validate_config_file_exists = MagicMock(return_value=True)
        s3_service._s3_client.delete_object = MagicMock()

        s3_service.delete_config_file("test_config.xlsx")

        s3_service._s3_client.delete_object.assert_called_once()

    def test_delete_config_file_not_found(self, s3_service):
        """Test deleting non-existent config file raises FileNotFoundError."""
        s3_service.validate_config_file_exists = MagicMock(return_value=False)

        with pytest.raises(
            FileNotFoundError, match="Configuration file not found in S3"
        ):
            s3_service.delete_config_file("nonexistent.xlsx")

    def test_list_config_files_with_metadata(self, s3_service):
        """Test listing config files with metadata."""
        s3_service._s3_client.list_objects_v2.return_value = {
            "Contents": [
                {
                    "Key": "config_graal/PLFSS_2024.xlsx",
                    "Size": 1024,
                    "LastModified": datetime(2024, 1, 1),
                },
                {
                    "Key": "config_graal/test.xlsx",
                    "Size": 2048,
                    "LastModified": datetime(2024, 2, 1),
                },
            ]
        }

        result = s3_service.list_config_files_with_metadata()

        assert len(result) == 2
        assert result[0]["key"] == "PLFSS_2024.xlsx"
        assert result[0]["size"] == 1024
        assert result[0]["file_type"] == "config"
        assert result[1]["key"] == "test.xlsx"


class TestS3ServiceDatabaseOperations:
    """Test suite for S3Service similarity database operations (async)."""

    @pytest.fixture
    def s3_service(self, mocker):
        """Create a mock S3Service instance for testing."""
        mocker.patch.dict(
            "os.environ",
            {
                "S3_BUCKET_NAME": "test-bucket",
                "S3_BUCKET_ENDPOINT": "https://s3.test.com",
                "S3_BUCKET_ACCESS_KEY": "test-key",
                "S3_BUCKET_SECRET_KEY": "test-secret",
                "S3_CONFIG_FOLDER": "config",
                "S3_SIMILARITY_DB_FOLDER": "similarity_dbs",
            },
        )

        mock_boto3_client = MagicMock()
        mock_boto3_client.head_bucket = MagicMock()
        mocker.patch("boto3.client", return_value=mock_boto3_client)

        mock_aioboto3_session = MagicMock()
        mocker.patch("aioboto3.Session", return_value=mock_aioboto3_session)

        service = S3Service()
        return service

    @pytest.mark.asyncio
    async def test_list_database_files_success(self, s3_service):
        """Test listing database files returns sorted names without extension."""
        # Mock async S3 client
        mock_s3_client = AsyncMock()
        mock_s3_client.list_objects_v2 = AsyncMock(
            return_value={
                "Contents": [
                    {"Key": "similarity_dbs/PLFSS/2023.parquet"},
                    {"Key": "similarity_dbs/PLFSS/2024.parquet"},
                    {"Key": "similarity_dbs/PLACSS/2023.parquet"},
                ]
            }
        )

        # Mock the context manager
        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_s3_client)
        mock_context.__aexit__ = AsyncMock()

        s3_service._aioboto3_session.client = MagicMock(return_value=mock_context)

        result = await s3_service.list_database_files()

        assert len(result) == 3
        assert "2023" in result
        assert "2024" in result
        # Names should not have .parquet extension
        assert not any(".parquet" in name for name in result)

    @pytest.mark.asyncio
    async def test_load_database_parquet_success(self, s3_service, mocker):
        """Test successful database loading from parquet."""
        # Create mock DataFrame
        mock_df = pd.DataFrame(
            {"amendment_id": [1, 2], "text": ["text1", "text2"], "score": [0.9, 0.8]}
        )

        # Mock parquet bytes
        buffer = BytesIO()
        mock_df.to_parquet(buffer, index=False)
        parquet_bytes = buffer.getvalue()

        # Mock response body
        mock_body = AsyncMock()
        mock_body.read = AsyncMock(return_value=parquet_bytes)

        # Mock async S3 client
        mock_s3_client = AsyncMock()
        mock_s3_client.get_object = AsyncMock(return_value={"Body": mock_body})

        # Mock the context manager
        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_s3_client)
        mock_context.__aexit__ = AsyncMock()

        s3_service._aioboto3_session.client = MagicMock(return_value=mock_context)

        result = await s3_service.load_database_parquet("PLFSS/2024")

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2
        assert "amendment_id" in result.columns
        mock_s3_client.get_object.assert_called_once()

    @pytest.mark.asyncio
    async def test_load_database_parquet_strips_extension(self, s3_service):
        """Test that .parquet extension is properly handled."""
        mock_body = AsyncMock()
        mock_df = pd.DataFrame({"col": [1, 2]})
        buffer = BytesIO()
        mock_df.to_parquet(buffer, index=False)
        mock_body.read = AsyncMock(return_value=buffer.getvalue())

        mock_s3_client = AsyncMock()
        mock_s3_client.get_object = AsyncMock(return_value={"Body": mock_body})

        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_s3_client)
        mock_context.__aexit__ = AsyncMock()

        s3_service._aioboto3_session.client = MagicMock(return_value=mock_context)

        # Test with .parquet extension
        await s3_service.load_database_parquet("PLFSS/2024.parquet")

        # Verify the key doesn't have double .parquet
        call_kwargs = mock_s3_client.get_object.call_args[1]
        assert call_kwargs["Key"] == "similarity_dbs/PLFSS/2024.parquet"

    @pytest.mark.asyncio
    async def test_load_database_parquet_not_found(self, s3_service):
        """Test loading non-existent database raises FileNotFoundError."""
        error_response = {"Error": {"Code": "NoSuchKey"}, "ResponseMetadata": {}}
        client_error = ClientError(error_response, "GetObject")

        mock_s3_client = AsyncMock()
        mock_s3_client.get_object = AsyncMock(side_effect=client_error)

        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_s3_client)
        mock_context.__aexit__ = AsyncMock(return_value=None)

        s3_service._aioboto3_session.client = MagicMock(return_value=mock_context)

        with pytest.raises(
            FileNotFoundError, match="Similarity database not found in S3"
        ):
            await s3_service.load_database_parquet("nonexistent/db")

    @pytest.mark.asyncio
    async def test_upload_database_parquet_success(self, s3_service, mocker):
        """Test successful database upload as parquet."""
        # Create test DataFrame
        test_df = pd.DataFrame({"col1": [1, 2], "col2": ["a", "b"]})

        # Mock async S3 client
        mock_s3_client = AsyncMock()
        mock_s3_client.put_object = AsyncMock()

        # Mock the context manager
        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_s3_client)
        mock_context.__aexit__ = AsyncMock()

        s3_service._aioboto3_session.client = MagicMock(return_value=mock_context)

        await s3_service.upload_database_parquet(test_df, "PLFSS/2024")

        # Verify put_object was called
        mock_s3_client.put_object.assert_called_once()
        call_kwargs = mock_s3_client.put_object.call_args[1]
        assert call_kwargs["Bucket"] == "test-bucket"
        assert call_kwargs["Key"] == "similarity_dbs/PLFSS/2024.parquet"
        assert isinstance(call_kwargs["Body"], bytes)

    @pytest.mark.asyncio
    async def test_get_database_metadata_success(self, s3_service):
        """Test getting database metadata."""
        mock_s3_client = AsyncMock()
        mock_s3_client.head_object = AsyncMock(
            return_value={
                "ContentLength": 10240,
                "LastModified": datetime(2024, 1, 1),
                "ETag": '"abc123"',
            }
        )

        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_s3_client)
        mock_context.__aexit__ = AsyncMock()

        s3_service._aioboto3_session.client = MagicMock(return_value=mock_context)

        result = await s3_service.get_database_metadata("PLFSS/2024")

        assert result["size"] == 10240
        assert result["last_modified"] == datetime(2024, 1, 1)
        assert result["etag"] == "abc123"

    @pytest.mark.asyncio
    async def test_delete_database_file_success(self, s3_service):
        """Test successful database deletion."""
        mock_s3_client = AsyncMock()
        mock_s3_client.head_object = AsyncMock()
        mock_s3_client.delete_object = AsyncMock()

        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_s3_client)
        mock_context.__aexit__ = AsyncMock()

        s3_service._aioboto3_session.client = MagicMock(return_value=mock_context)

        await s3_service.delete_database_file("PLFSS/2024")

        mock_s3_client.delete_object.assert_called_once()


class TestS3ServiceDataFrameSanitization:
    """Test suite for DataFrame sanitization before Parquet conversion."""

    @pytest.fixture
    def s3_service(self, mocker):
        """Create a mock S3Service instance for testing."""
        mocker.patch.dict(
            "os.environ",
            {
                "S3_BUCKET_NAME": "test-bucket",
                "S3_BUCKET_ENDPOINT": "https://s3.test.com",
                "S3_BUCKET_ACCESS_KEY": "test-key",
                "S3_BUCKET_SECRET_KEY": "test-secret",
                "S3_CONFIG_FOLDER": "config",
                "S3_SIMILARITY_DB_FOLDER": "similarity_dbs",
            },
        )

        mock_boto3_client = MagicMock()
        mock_boto3_client.head_bucket = MagicMock()
        mocker.patch("boto3.client", return_value=mock_boto3_client)

        mock_aioboto3_session = MagicMock()
        mocker.patch("aioboto3.Session", return_value=mock_aioboto3_session)

        service = S3Service()
        return service

    def test_prepare_dataframe_converts_bytes_to_string(self, s3_service):
        """Test that bytes are converted to UTF-8 strings."""
        df = pd.DataFrame({"text": [b"hello", b"world", "normal"]})

        result = s3_service._prepare_dataframe_for_parquet(df)

        assert result["text"][0] == "hello"
        assert result["text"][1] == "world"
        assert result["text"][2] == "normal"

    def test_prepare_dataframe_preserves_nulls(self, s3_service):
        """Test that NaN/None values are preserved."""
        df = pd.DataFrame({"col1": [1, None, 3], "col2": ["a", None, "c"]})

        result = s3_service._prepare_dataframe_for_parquet(df)

        assert pd.isna(result["col1"][1])
        assert pd.isna(result["col2"][1])

    def test_prepare_dataframe_converts_mixed_object_to_string(self, s3_service):
        """Test that mixed object columns are converted to string dtype."""
        df = pd.DataFrame({"mixed": [1, "text", None, b"bytes"]})

        result = s3_service._prepare_dataframe_for_parquet(df)

        # Check that all non-null values are strings
        assert result["mixed"][0] == "1"
        assert result["mixed"][1] == "text"
        assert pd.isna(result["mixed"][2])
        assert result["mixed"][3] == "bytes"

    def test_prepare_dataframe_handles_bytearray(self, s3_service):
        """Test that bytearray is converted properly."""
        df = pd.DataFrame({"data": [bytearray(b"test"), "normal"]})

        result = s3_service._prepare_dataframe_for_parquet(df)

        assert result["data"][0] == "test"
        assert result["data"][1] == "normal"

    def test_prepare_dataframe_uses_string_dtype(self, s3_service):
        """Test that object columns are converted to pandas string dtype."""
        df = pd.DataFrame({"text": ["hello", "world", None]})

        result = s3_service._prepare_dataframe_for_parquet(df)

        # Check that it uses pandas nullable string dtype
        assert result["text"].dtype == "string"

    def test_prepare_dataframe_doesnt_modify_numeric_columns(self, s3_service):
        """Test that numeric columns are left unchanged."""
        df = pd.DataFrame(
            {
                "int_col": [1, 2, 3],
                "float_col": [1.1, 2.2, 3.3],
                "text": ["a", "b", "c"],
            }
        )

        result = s3_service._prepare_dataframe_for_parquet(df)

        assert result["int_col"].dtype == df["int_col"].dtype
        assert result["float_col"].dtype == df["float_col"].dtype


class TestS3ServiceInputPoolExtended:
    """Extended tests for input pool operations."""

    @pytest.fixture
    def s3_service(self, mocker):
        """Create a mock S3Service instance for testing."""
        mocker.patch.dict(
            "os.environ",
            {
                "S3_BUCKET_NAME": "test-bucket",
                "S3_BUCKET_ENDPOINT": "https://s3.test.com",
                "S3_BUCKET_ACCESS_KEY": "test-key",
                "S3_BUCKET_SECRET_KEY": "test-secret",
                "S3_CONFIG_FOLDER": "config",
                "S3_SIMILARITY_DB_FOLDER": "similarity_dbs",
                "S3_INPUT_POOL_FOLDER": "input_files/pool",
            },
        )

        mock_boto3_client = MagicMock()
        mock_boto3_client.head_bucket = MagicMock()
        mocker.patch("boto3.client", return_value=mock_boto3_client)

        mock_aioboto3_session = MagicMock()
        mocker.patch("aioboto3.Session", return_value=mock_aioboto3_session)

        service = S3Service()
        return service

    @pytest.mark.asyncio
    async def test_list_pool_files_by_hash_prefix(self, s3_service):
        """Test listing files by hash prefix."""
        mock_s3_client = AsyncMock()
        mock_s3_client.list_objects_v2 = AsyncMock(
            return_value={
                "Contents": [
                    {"Key": "input_files/pool/abc123.json"},
                    {"Key": "input_files/pool/abc123.xlsx"},
                ]
            }
        )

        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_s3_client)
        mock_context.__aexit__ = AsyncMock()

        s3_service._aioboto3_session.client = MagicMock(return_value=mock_context)

        result = await s3_service.list_pool_files_by_hash_prefix("abc123")

        assert len(result) == 2
        assert "abc123.json" in result
        assert "abc123.xlsx" in result

    @pytest.mark.asyncio
    async def test_get_input_pool_metadata_success(self, s3_service):
        """Test getting input pool file metadata."""
        mock_s3_client = AsyncMock()
        mock_s3_client.head_object = AsyncMock(
            return_value={
                "ContentLength": 2048,
                "LastModified": datetime(2024, 1, 1),
                "ContentType": "application/json",
                "ETag": '"xyz789"',
            }
        )

        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_s3_client)
        mock_context.__aexit__ = AsyncMock()

        s3_service._aioboto3_session.client = MagicMock(return_value=mock_context)

        result = await s3_service.get_input_pool_metadata("abc123.json")

        assert result["size"] == 2048
        assert result["content_type"] == "application/json"
        assert result["etag"] == "xyz789"

    @pytest.mark.asyncio
    async def test_list_input_pool_files_with_metadata(self, s3_service):
        """Test listing all input pool files with metadata."""
        mock_s3_client = AsyncMock()
        mock_s3_client.list_objects_v2 = AsyncMock(
            return_value={
                "Contents": [
                    {
                        "Key": "input_files/pool/file1.json",
                        "Size": 1024,
                        "LastModified": datetime(2024, 1, 1),
                    },
                    {
                        "Key": "input_files/pool/file2.xlsx",
                        "Size": 2048,
                        "LastModified": datetime(2024, 1, 2),
                    },
                ]
            }
        )

        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_s3_client)
        mock_context.__aexit__ = AsyncMock()

        s3_service._aioboto3_session.client = MagicMock(return_value=mock_context)

        result = await s3_service.list_input_pool_files_with_metadata()

        assert len(result) == 2
        assert result[0]["key"] == "file1.json"
        assert result[0]["file_type"] == "input_file"
        assert result[1]["key"] == "file2.xlsx"

    @pytest.mark.asyncio
    async def test_delete_input_pool_file_success(self, s3_service):
        """Test successful deletion of input pool file."""
        mock_s3_client = AsyncMock()
        mock_s3_client.head_object = AsyncMock()
        mock_s3_client.delete_object = AsyncMock()

        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_s3_client)
        mock_context.__aexit__ = AsyncMock()

        s3_service._aioboto3_session.client = MagicMock(return_value=mock_context)

        await s3_service.delete_input_pool_file("abc123.json")

        mock_s3_client.delete_object.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_input_pool_file_not_found(self, s3_service):
        """Test deleting non-existent input pool file."""
        error_response = {"Error": {"Code": "404"}, "ResponseMetadata": {}}
        client_error = ClientError(error_response, "HeadObject")

        mock_s3_client = AsyncMock()
        mock_s3_client.head_object = AsyncMock(side_effect=client_error)

        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_s3_client)
        mock_context.__aexit__ = AsyncMock(return_value=None)

        s3_service._aioboto3_session.client = MagicMock(return_value=mock_context)

        with pytest.raises(FileNotFoundError, match="File not found in input pool"):
            await s3_service.delete_input_pool_file("nonexistent.json")
