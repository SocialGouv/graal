import asyncio
import logging
from io import BytesIO
from typing import Any, Dict, List

import boto3
import pandas as pd
from botocore.config import Config
from botocore.exceptions import ClientError


class ConfigS3Service:
    """
    Service responsible for handling configuration Excel files stored in S3.
    """

    def __init__(
        self,
        bucket_name: str,
        endpoint_url: str,
        config_folder: str,
        s3_config: Config,
        region_name: str,
        access_key: str,
        secret_key: str,
    ):
        self.bucket_name = bucket_name
        self.endpoint_url = endpoint_url
        self.config_folder = config_folder
        self.s3_config = s3_config
        self.region_name = region_name
        self.access_key = access_key
        self.secret_key = secret_key

    # -------------------------------------------------------------------------
    # Internal helper: create fresh boto3 client
    # -------------------------------------------------------------------------
    def _new_client(self):
        return boto3.client(
            "s3",
            endpoint_url=self.endpoint_url,
            region_name=self.region_name,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            config=self.s3_config,
        )

    def build_config_key(self, filename: str) -> str:
        if not self.config_folder.endswith("/"):
            return f"{self.config_folder}/{filename}"
        return f"{self.config_folder}{filename}"

    # -------------------------------------------------------------------------
    # Internal helper: synchronous S3 download (wrapped by asyncio.to_thread)
    # -------------------------------------------------------------------------
    def _download_from_s3_sync(self, s3_key: str) -> BytesIO:
        client = self._new_client()
        try:
            logging.info(f"Downloading file from S3: s3://{self.bucket_name}/{s3_key}")
            response = client.get_object(Bucket=self.bucket_name, Key=s3_key)
            file_content = BytesIO(response["Body"].read())
            return file_content
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                raise FileNotFoundError(f"File not found in S3: {s3_key}") from e
            raise

    # -------------------------------------------------------------------------
    # Public API: list config files
    # -------------------------------------------------------------------------
    async def list_available_config_files(self) -> List[str]:
        def _list_sync():
            client = self._new_client()
            prefix = (
                self.config_folder
                if self.config_folder.endswith("/")
                else f"{self.config_folder}/"
            )
            response = client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix,
            )
            files = []
            if "Contents" in response:
                for obj in response["Contents"]:
                    filename = obj["Key"].split("/")[-1]
                    if filename.endswith(".xlsx"):
                        files.append(filename)
            return sorted(files)

        return await asyncio.to_thread(_list_sync)

    # -------------------------------------------------------------------------
    # Public API: check existence
    # -------------------------------------------------------------------------
    async def validate_config_file_exists(self, filename: str) -> bool:
        def _exists_sync():
            client = self._new_client()
            key = self.build_config_key(filename)
            try:
                client.head_object(Bucket=self.bucket_name, Key=key)
                return True
            except ClientError as e:
                if e.response["Error"]["Code"] == "404":
                    return False
                raise

        return await asyncio.to_thread(_exists_sync)

    # -------------------------------------------------------------------------
    # Public API: load Excel config file
    # -------------------------------------------------------------------------
    async def load_config_excel(self, filename: str) -> Dict[str, pd.DataFrame]:
        def _load_sync():
            key = self.build_config_key(filename)
            file_bytes = self._download_from_s3_sync(key)
            return pd.read_excel(file_bytes, sheet_name=None)

        return await asyncio.to_thread(_load_sync)

    # -------------------------------------------------------------------------
    # Public API: list config files with metadata
    # -------------------------------------------------------------------------
    async def list_config_files_with_metadata(self) -> List[Dict[str, Any]]:
        def _list_meta_sync():
            client = self._new_client()
            prefix = (
                self.config_folder
                if self.config_folder.endswith("/")
                else f"{self.config_folder}/"
            )
            response = client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix,
            )
            files = []
            if "Contents" in response:
                for obj in response["Contents"]:
                    filename = obj["Key"].split("/")[-1]
                    if filename.endswith(".xlsx"):
                        files.append(
                            {
                                "key": filename,
                                "size": obj.get("Size", 0),
                                "last_modified": obj.get("LastModified"),
                                "file_type": "config",
                            }
                        )
            return sorted(files, key=lambda x: x["key"])

        return await asyncio.to_thread(_list_meta_sync)

    # -------------------------------------------------------------------------
    # Public API: upload Excel config file
    # -------------------------------------------------------------------------
    async def upload_config_file(self, filename: str, content: bytes) -> str:
        """Upload an Excel configuration file to S3.

        Args:
            filename: File name relative to the config folder
            content: Raw XLSX bytes

        Returns:
            The stored filename (same as input)
        """

        def _upload_sync() -> str:
            client = self._new_client()
            key = self.build_config_key(filename)
            client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=content,
                ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
            return filename

        return await asyncio.to_thread(_upload_sync)

    async def upload_config_file_by_key(self, s3_key: str, content: bytes) -> str:
        """Upload an Excel configuration file using a full S3 key."""

        def _upload_sync() -> str:
            client = self._new_client()
            client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=content,
                ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
            return s3_key

        return await asyncio.to_thread(_upload_sync)

    # -------------------------------------------------------------------------
    # Public API: download raw Excel bytes
    # -------------------------------------------------------------------------
    async def download_config_file(self, filename: str) -> bytes:
        def _download_bytes_sync() -> bytes:
            key = self.build_config_key(filename)
            buffer = self._download_from_s3_sync(key)
            return buffer.getvalue()

        return await asyncio.to_thread(_download_bytes_sync)

    # -------------------------------------------------------------------------
    # Public API: delete config file
    # -------------------------------------------------------------------------
    async def delete_config_file(self, filename: str) -> None:
        def _delete_sync():
            client = self._new_client()
            key = self.build_config_key(filename)
            client.delete_object(Bucket=self.bucket_name, Key=key)

        await asyncio.to_thread(_delete_sync)

    async def delete_config_file_by_key(self, s3_key: str) -> None:
        def _delete_sync():
            client = self._new_client()
            client.delete_object(Bucket=self.bucket_name, Key=s3_key)

        await asyncio.to_thread(_delete_sync)
