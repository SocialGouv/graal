from typing import Any, Dict, List

import aioboto3
from botocore.config import Config
from botocore.exceptions import ClientError


class InputPoolS3Service:
    """
    Async-only S3 service for handling input file pool operations (upload, download, listing, metadata)
    """

    def __init__(
        self,
        bucket_name: str,
        endpoint_url: str,
        input_pool_folder: str,
        s3_config: Config,
        region_name: str = "gra",
        access_key: str | None = None,
        secret_key: str | None = None,
    ):
        self.bucket_name = bucket_name
        self.endpoint_url = endpoint_url
        self.input_pool_folder = input_pool_folder
        self.s3_config = s3_config
        self.region_name = region_name
        self.access_key = access_key
        self.secret_key = secret_key

    # -------------------------------------------------------------------------
    # Internal helper: fresh session
    # -------------------------------------------------------------------------
    def _new_session(self):
        return aioboto3.Session(
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            region_name=self.region_name,
        )

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------
    def _pool_key(self, s3_key: str) -> str:
        if self.input_pool_folder.endswith("/"):
            return f"{self.input_pool_folder}{s3_key}"
        return f"{self.input_pool_folder}/{s3_key}"

    # -------------------------------------------------------------------------
    # INPUT POOL: Upload file
    # -------------------------------------------------------------------------
    async def upload_to_input_pool(self, file_content: bytes, s3_key: str) -> None:
        full_key = self._pool_key(s3_key)

        async with self._new_session().client(
            "s3",
            endpoint_url=self.endpoint_url,
            config=self.s3_config,
        ) as client:
            await client.put_object(
                Bucket=self.bucket_name,
                Key=full_key,
                Body=file_content,
            )

    # -------------------------------------------------------------------------
    # INPUT POOL: Download
    # -------------------------------------------------------------------------
    async def download_from_input_pool(self, s3_key: str) -> bytes:
        full_key = self._pool_key(s3_key)

        async with self._new_session().client(
            "s3",
            endpoint_url=self.endpoint_url,
            config=self.s3_config,
        ) as client:
            response = await client.get_object(
                Bucket=self.bucket_name,
                Key=full_key,
            )
            file_bytes = await response["Body"].read()

        return file_bytes

    # -------------------------------------------------------------------------
    # INPUT POOL: List by hash prefix
    # -------------------------------------------------------------------------
    async def list_pool_files_by_hash_prefix(self, file_hash: str) -> List[str]:
        prefix = (
            f"{self.input_pool_folder}{file_hash}"
            if self.input_pool_folder.endswith("/")
            else f"{self.input_pool_folder}/{file_hash}"
        )

        async with self._new_session().client(
            "s3",
            endpoint_url=self.endpoint_url,
            config=self.s3_config,
        ) as client:
            response = await client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix,
                MaxKeys=50,
            )

        files = []
        if "Contents" in response:
            for obj in response["Contents"]:
                full_key = obj["Key"]
                if full_key.startswith(f"{self.input_pool_folder}/"):
                    relative = full_key[len(self.input_pool_folder) + 1 :]
                elif full_key.startswith(self.input_pool_folder):
                    relative = full_key[len(self.input_pool_folder) :]
                else:
                    relative = full_key
                files.append(relative)

        return files

    # -------------------------------------------------------------------------
    # INPUT POOL: Metadata
    # -------------------------------------------------------------------------
    async def get_input_pool_metadata(self, s3_key: str) -> Dict[str, Any]:
        full_key = self._pool_key(s3_key)

        async with self._new_session().client(
            "s3",
            endpoint_url=self.endpoint_url,
            config=self.s3_config,
        ) as client:
            response = await client.head_object(
                Bucket=self.bucket_name,
                Key=full_key,
            )

        return {
            "size": response.get("ContentLength", 0),
            "last_modified": response.get("LastModified"),
            "content_type": response.get("ContentType"),
            "etag": response.get("ETag", "").strip('"'),
        }

    # -------------------------------------------------------------------------
    # INPUT POOL: Exists check
    # -------------------------------------------------------------------------
    async def file_exists_in_pool(self, s3_key: str) -> bool:
        full_key = self._pool_key(s3_key)

        async with self._new_session().client(
            "s3",
            endpoint_url=self.endpoint_url,
            config=self.s3_config,
        ) as client:
            try:
                await client.head_object(
                    Bucket=self.bucket_name,
                    Key=full_key,
                )
                return True
            except ClientError as e:
                if e.response["Error"]["Code"] == "404":
                    return False
                raise

    # -------------------------------------------------------------------------
    # INPUT POOL: List with metadata
    # -------------------------------------------------------------------------
    async def list_input_pool_files_with_metadata(self) -> List[Dict[str, Any]]:
        prefix = (
            self.input_pool_folder
            if self.input_pool_folder.endswith("/")
            else f"{self.input_pool_folder}/"
        )

        async with self._new_session().client(
            "s3",
            endpoint_url=self.endpoint_url,
            config=self.s3_config,
        ) as client:
            response = await client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix,
            )

        results = []
        if "Contents" in response:
            for obj in response["Contents"]:
                full_key = obj["Key"]
                if full_key.startswith(f"{self.input_pool_folder}/"):
                    relative = full_key[len(self.input_pool_folder) + 1 :]
                elif full_key.startswith(self.input_pool_folder):
                    relative = full_key[len(self.input_pool_folder) :]
                else:
                    relative = full_key

                if relative:
                    results.append(
                        {
                            "key": relative,
                            "size": obj.get("Size", 0),
                            "last_modified": obj.get("LastModified"),
                            "file_type": "input_file",
                        }
                    )

        return sorted(results, key=lambda x: x["key"])

    # -------------------------------------------------------------------------
    # INPUT POOL: Delete file
    # -------------------------------------------------------------------------
    async def delete_input_pool_file(self, s3_key: str) -> None:
        full_key = self._pool_key(s3_key)

        async with self._new_session().client(
            "s3",
            endpoint_url=self.endpoint_url,
            config=self.s3_config,
        ) as client:
            await client.head_object(
                Bucket=self.bucket_name,
                Key=full_key,
            )
            await client.delete_object(
                Bucket=self.bucket_name,
                Key=full_key,
            )
