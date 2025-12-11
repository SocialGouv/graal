from datetime import datetime
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock

import pandas as pd
import aioboto3
import pytest

from graal.utils.s3.database_s3_service import DatabaseS3Service


@pytest.fixture
def db_s3(mocker):
    mocker.patch.dict(
        "os.environ",
        {
            "S3_BUCKET_NAME": "test-bucket",
            "S3_BUCKET_ENDPOINT": "https://s3.test.com",
            "S3_BUCKET_ACCESS_KEY": "test-key",
            "S3_BUCKET_SECRET_KEY": "test-secret",
            "S3_SIMILARITY_DB_FOLDER": "similarity_dbs",
        },
    )

    mock_aioboto3_session = MagicMock()
    mocker.patch("aioboto3.Session", return_value=mock_aioboto3_session)

    from botocore.config import Config

    service = DatabaseS3Service(
        bucket_name="test-bucket",
        endpoint_url="https://s3.test.com",
        similarity_db_folder="similarity_dbs",
        s3_config=Config(s3={"addressing_style": "path"}),
        region_name="gra",
        access_key="test-key",
        secret_key="test-secret",  # noqa: S106
    )
    return service


@pytest.mark.asyncio
async def test_list_database_files_success(db_s3):
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

    mock_context = AsyncMock()
    mock_context.__aenter__ = AsyncMock(return_value=mock_s3_client)
    mock_context.__aexit__ = AsyncMock()
    aioboto3.Session.return_value.client = MagicMock(return_value=mock_context)

    result = await db_s3.list_database_files()

    assert len(result) == 3
    assert "2023" in result
    assert "2024" in result
    assert not any(".parquet" in name for name in result)


@pytest.mark.asyncio
async def test_load_database_parquet_success(db_s3, mocker):
    mock_df = pd.DataFrame(
        {"amendment_id": [1, 2], "text": ["text1", "text2"], "score": [0.9, 0.8]}
    )
    buffer = BytesIO()
    mock_df.to_parquet(buffer, index=False)
    parquet_bytes = buffer.getvalue()

    mock_body = AsyncMock()
    mock_body.read = AsyncMock(return_value=parquet_bytes)

    mock_s3_client = AsyncMock()
    mock_s3_client.get_object = AsyncMock(return_value={"Body": mock_body})

    mock_context = AsyncMock()
    mock_context.__aenter__ = AsyncMock(return_value=mock_s3_client)
    mock_context.__aexit__ = AsyncMock()
    aioboto3.Session.return_value.client = MagicMock(return_value=mock_context)

    result = await db_s3.load_database_parquet("PLFSS/2024")

    assert isinstance(result, pd.DataFrame)
    assert len(result) == 2
    assert "amendment_id" in result.columns


@pytest.mark.asyncio
async def test_load_database_parquet_strips_extension(db_s3):
    mock_df = pd.DataFrame({"col": [1, 2]})
    buffer = BytesIO()
    mock_df.to_parquet(buffer, index=False)

    mock_body = AsyncMock()
    mock_body.read = AsyncMock(return_value=buffer.getvalue())

    mock_s3_client = AsyncMock()
    mock_s3_client.get_object = AsyncMock(return_value={"Body": mock_body})

    mock_context = AsyncMock()
    mock_context.__aenter__ = AsyncMock(return_value=mock_s3_client)
    mock_context.__aexit__ = AsyncMock()
    aioboto3.Session.return_value.client = MagicMock(return_value=mock_context)

    await db_s3.load_database_parquet("PLFSS/2024.parquet")

    call_kwargs = mock_s3_client.get_object.call_args[1]
    assert call_kwargs["Key"] == "similarity_dbs/PLFSS/2024.parquet"


@pytest.mark.asyncio
async def test_upload_database_parquet_success(db_s3):
    test_df = pd.DataFrame({"col1": [1, 2], "col2": ["a", "b"]})

    mock_s3_client = AsyncMock()
    mock_s3_client.put_object = AsyncMock()

    mock_context = AsyncMock()
    mock_context.__aenter__ = AsyncMock(return_value=mock_s3_client)
    mock_context.__aexit__ = AsyncMock()
    aioboto3.Session.return_value.client = MagicMock(return_value=mock_context)

    await db_s3.upload_database_parquet(test_df, "PLFSS/2024")

    call_kwargs = mock_s3_client.put_object.call_args[1]
    assert call_kwargs["Bucket"] == "test-bucket"
    assert call_kwargs["Key"] == "similarity_dbs/PLFSS/2024.parquet"
    assert isinstance(call_kwargs["Body"], bytes)


@pytest.mark.asyncio
async def test_get_database_metadata_success(db_s3):
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
    aioboto3.Session.return_value.client = MagicMock(return_value=mock_context)

    result = await db_s3.get_database_metadata("PLFSS/2024")

    assert result["size"] == 10240
    assert result["last_modified"] == datetime(2024, 1, 1)
    assert result["etag"] == "abc123"


@pytest.mark.asyncio
async def test_delete_database_file_success(db_s3):
    mock_s3_client = AsyncMock()
    mock_s3_client.head_object = AsyncMock()
    mock_s3_client.delete_object = AsyncMock()

    mock_context = AsyncMock()
    mock_context.__aenter__ = AsyncMock(return_value=mock_s3_client)
    mock_context.__aexit__ = AsyncMock()
    aioboto3.Session.return_value.client = MagicMock(return_value=mock_context)

    await db_s3.delete_database_file("PLFSS/2024")

    mock_s3_client.delete_object.assert_called_once()
