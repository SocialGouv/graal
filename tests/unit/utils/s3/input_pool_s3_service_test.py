from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from botocore.config import Config
from botocore.exceptions import ClientError

from graal.utils.s3.input_pool_s3_service import InputPoolS3Service


@pytest.fixture
def input_pool_s3(mocker):
    mocker.patch.dict(
        "os.environ",
        {
            "S3_BUCKET_NAME": "test-bucket",
            "S3_BUCKET_ENDPOINT": "https://s3.test.com",
            "S3_BUCKET_ACCESS_KEY": "test-key",
            "S3_BUCKET_SECRET_KEY": "test-secret",
            "S3_INPUT_POOL_FOLDER": "input_files/pool",
        },
    )

    # mock session factory
    mock_aioboto3_session = MagicMock()
    mocker.patch("aioboto3.Session", return_value=mock_aioboto3_session)

    service = InputPoolS3Service(
        bucket_name="test-bucket",
        endpoint_url="https://s3.test.com",
        input_pool_folder="input_files/pool",
        s3_config=Config(s3={"addressing_style": "path"}),
        region_name="gra",
        access_key="test-key",
        secret_key="test-secret",  # noqa: S106
    )
    return service


@pytest.mark.asyncio
async def test_upload_to_input_pool_success(input_pool_s3):
    mock_s3_client = AsyncMock()
    mock_s3_client.put_object = AsyncMock()

    mock_context = AsyncMock()
    mock_context.__aenter__ = AsyncMock(return_value=mock_s3_client)
    mock_context.__aexit__ = AsyncMock()

    session = MagicMock()
    session.client = MagicMock(return_value=mock_context)
    input_pool_s3._new_session = MagicMock(return_value=session)

    await input_pool_s3.upload_to_input_pool(b"hello", "file.json")

    mock_s3_client.put_object.assert_called_once()
    call = mock_s3_client.put_object.call_args[1]
    assert call["Bucket"] == "test-bucket"
    assert call["Key"] == "input_files/pool/file.json"
    assert call["Body"] == b"hello"


@pytest.mark.asyncio
async def test_download_from_input_pool_success(input_pool_s3):
    mock_body = AsyncMock()
    mock_body.read = AsyncMock(return_value=b"content")

    mock_s3_client = AsyncMock()
    mock_s3_client.get_object = AsyncMock(return_value={"Body": mock_body})

    mock_context = AsyncMock()
    mock_context.__aenter__ = AsyncMock(return_value=mock_s3_client)
    mock_context.__aexit__ = AsyncMock()

    session = MagicMock()
    session.client = MagicMock(return_value=mock_context)
    input_pool_s3._new_session = MagicMock(return_value=session)

    result = await input_pool_s3.download_from_input_pool("abc.json")
    assert result == b"content"


@pytest.mark.asyncio
async def test_file_exists_in_pool_true(input_pool_s3):
    mock_s3_client = AsyncMock()
    mock_s3_client.head_object = AsyncMock()

    mock_context = AsyncMock()
    mock_context.__aenter__ = AsyncMock(return_value=mock_s3_client)
    mock_context.__aexit__ = AsyncMock()

    session = MagicMock()
    session.client = MagicMock(return_value=mock_context)
    input_pool_s3._new_session = MagicMock(return_value=session)

    assert await input_pool_s3.file_exists_in_pool("abc.json") is True


@pytest.mark.asyncio
async def test_file_exists_in_pool_false(input_pool_s3):
    error_response = {"Error": {"Code": "404"}}
    client_error = ClientError(error_response, "HeadObject")

    mock_s3_client = AsyncMock()
    mock_s3_client.head_object = AsyncMock(side_effect=client_error)

    mock_context = AsyncMock()
    mock_context.__aenter__ = AsyncMock(return_value=mock_s3_client)
    mock_context.__aexit__ = AsyncMock()

    session = MagicMock()
    session.client = MagicMock(return_value=mock_context)
    input_pool_s3._new_session = MagicMock(return_value=session)

    assert await input_pool_s3.file_exists_in_pool("missing.json") is False


@pytest.mark.asyncio
async def test_list_pool_files_by_hash_prefix(input_pool_s3):
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

    session = MagicMock()
    session.client = MagicMock(return_value=mock_context)
    input_pool_s3._new_session = MagicMock(return_value=session)

    result = await input_pool_s3.list_pool_files_by_hash_prefix("abc123")
    assert "abc123.json" in result
    assert "abc123.xlsx" in result


@pytest.mark.asyncio
async def test_get_input_pool_metadata(input_pool_s3):
    mock_s3_client = AsyncMock()
    mock_s3_client.head_object = AsyncMock(
        return_value={
            "ContentLength": 2048,
            "LastModified": datetime(2024, 1, 1),
            "ContentType": "application/json",
            "ETag": '"xyz"',
        }
    )

    mock_context = AsyncMock()
    mock_context.__aenter__ = AsyncMock(return_value=mock_s3_client)
    mock_context.__aexit__ = AsyncMock()

    session = MagicMock()
    session.client = MagicMock(return_value=mock_context)
    input_pool_s3._new_session = MagicMock(return_value=session)

    meta = await input_pool_s3.get_input_pool_metadata("file.json")
    assert meta["size"] == 2048
    assert meta["content_type"] == "application/json"
    assert meta["etag"] == "xyz"


@pytest.mark.asyncio
async def test_list_input_pool_files_with_metadata(input_pool_s3):
    mock_s3_client = AsyncMock()
    mock_s3_client.list_objects_v2 = AsyncMock(
        return_value={
            "Contents": [
                {
                    "Key": "input_files/pool/file1.json",
                    "Size": 100,
                    "LastModified": datetime(2024, 1, 1),
                },
                {
                    "Key": "input_files/pool/file2.xlsx",
                    "Size": 300,
                    "LastModified": datetime(2024, 1, 2),
                },
            ]
        }
    )

    mock_context = AsyncMock()
    mock_context.__aenter__ = AsyncMock(return_value=mock_s3_client)
    mock_context.__aexit__ = AsyncMock()

    session = MagicMock()
    session.client = MagicMock(return_value=mock_context)
    input_pool_s3._new_session = MagicMock(return_value=session)

    result = await input_pool_s3.list_input_pool_files_with_metadata()
    assert len(result) == 2
    assert result[0]["key"] == "file1.json"
    assert result[1]["key"] == "file2.xlsx"


@pytest.mark.asyncio
async def test_delete_input_pool_file_success(input_pool_s3):
    mock_s3_client = AsyncMock()
    mock_s3_client.head_object = AsyncMock()
    mock_s3_client.delete_object = AsyncMock()

    mock_context = AsyncMock()
    mock_context.__aenter__ = AsyncMock(return_value=mock_s3_client)
    mock_context.__aexit__ = AsyncMock()

    session = MagicMock()
    session.client = MagicMock(return_value=mock_context)
    input_pool_s3._new_session = MagicMock(return_value=session)

    await input_pool_s3.delete_input_pool_file("abc.json")
    mock_s3_client.delete_object.assert_called_once()
