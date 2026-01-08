from io import BytesIO
from unittest.mock import MagicMock

import pandas as pd
import pytest

from graal.utils.s3.config_s3_service import ConfigS3Service


class TestConfigS3Service:
    """Tests for ConfigS3Service (synchronous methods)."""

    @pytest.fixture
    def config_service(self, mocker):
        mocker.patch.dict(
            "os.environ",
            {
                "S3_BUCKET_NAME": "test-bucket",
                "S3_BUCKET_ENDPOINT": "https://s3.test.com",
                "S3_BUCKET_ACCESS_KEY": "test-key",
                "S3_BUCKET_SECRET_KEY": "test-secret",
                "S3_CONFIG_FOLDER": "config_graal",
            },
        )

        mock_boto3_client = MagicMock()
        mock_boto3_client.head_bucket = MagicMock()
        mocker.patch("boto3.client", return_value=mock_boto3_client)

        service = ConfigS3Service(
            bucket_name="test-bucket",
            region_name="gra",
            access_key="test-key",
            secret_key="test-secret",  # noqa: S106
            endpoint_url="https://s3.test.com",
            config_folder="config_graal",
            s3_config=None,
        )
        # inject mocked underlying boto3 client
        service._new_client = MagicMock(return_value=mock_boto3_client)
        return service

    @pytest.mark.asyncio
    async def test_list_available_config_files_success(self, config_service):
        config_service._new_client().list_objects_v2.return_value = {
            "Contents": [
                {"Key": "config_graal/PLFSS_2024.xlsx"},
                {"Key": "config_graal/PLACSS_2023.xlsx"},
                {"Key": "config_graal/test_config.xlsx"},
            ]
        }

        result = await config_service.list_available_config_files()

        assert result == ["PLACSS_2023.xlsx", "PLFSS_2024.xlsx", "test_config.xlsx"]

    @pytest.mark.asyncio
    async def test_list_available_config_files_empty(self, config_service):
        config_service._new_client().list_objects_v2.return_value = {}

        result = await config_service.list_available_config_files()
        assert result == []

    @pytest.mark.asyncio
    async def test_list_available_config_files_filters_non_xlsx(self, config_service):
        config_service._new_client().list_objects_v2.return_value = {
            "Contents": [
                {"Key": "config_graal/PLFSS_2024.xlsx"},
                {"Key": "config_graal/README.md"},
                {"Key": "config_graal/data.csv"},
            ]
        }

        result = await config_service.list_available_config_files()
        assert result == ["PLFSS_2024.xlsx"]

    @pytest.mark.asyncio
    async def test_validate_config_file_exists_true(self, config_service):
        client = config_service._new_client()
        client.head_object = MagicMock()

        result = await config_service.validate_config_file_exists("file.xlsx")
        assert result is True

    @pytest.mark.asyncio
    async def test_load_config_excel_success(self, config_service, mocker):
        mock_file_content = BytesIO(b"fake excel")
        config_service._download_from_s3_sync = MagicMock(
            return_value=mock_file_content
        )

        mock_df = pd.DataFrame({"A": [1, 2]})
        mocker.patch("pandas.read_excel", return_value={"Sheet1": mock_df})

        result = await config_service.load_config_excel("test.xlsx")

        assert "Sheet1" in result
        assert isinstance(result["Sheet1"], pd.DataFrame)

    @pytest.mark.asyncio
    async def test_delete_config_file_success(self, config_service, mocker):
        client = config_service._new_client()
        client.delete_object = MagicMock()

        await config_service.delete_config_file("test.xlsx")
        client.delete_object.assert_called_once()
