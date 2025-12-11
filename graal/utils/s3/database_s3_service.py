import asyncio
import logging
from io import BytesIO
from typing import Any, Dict, List

import aioboto3
import pandas as pd
from botocore.config import Config


class DatabaseS3Service:
    """
    Service responsible for handling similarity database parquet files stored in S3.
    """

    def __init__(
        self,
        bucket_name: str,
        endpoint_url: str,
        similarity_db_folder: str,
        s3_config: Config,
        region_name: str = "gra",
        access_key: str | None = None,
        secret_key: str | None = None,
    ):
        self.bucket_name = bucket_name
        self.endpoint_url = endpoint_url
        self.similarity_db_folder = similarity_db_folder
        self.s3_config = s3_config
        self.region_name = region_name
        self.access_key = access_key
        self.secret_key = secret_key

    # -------------------------------------------------------------------------
    # Internal helper: create fresh async session
    # -------------------------------------------------------------------------
    def _new_session(self):
        return aioboto3.Session(
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            region_name=self.region_name,
        )

    # -------------------------------------------------------------------------
    # Internal: prepare dataframe for parquet writing
    # -------------------------------------------------------------------------
    def _prepare_dataframe_for_parquet(self, df: pd.DataFrame) -> pd.DataFrame:
        df_out = df.copy()
        for col in df_out.columns:
            s = df_out[col]
            if s.dtype == "object":
                if (
                    getattr(s, "apply", None)
                    and s.apply(lambda v: isinstance(v, (bytes, bytearray))).any()
                ):
                    s = s.apply(
                        lambda v: v.decode("utf-8", "replace")
                        if isinstance(v, (bytes, bytearray))
                        else v
                    )

                if not pd.api.types.is_string_dtype(s):
                    s = s.map(lambda v: None if pd.isna(v) else str(v))
                try:
                    s = s.astype("string")
                except Exception as e:
                    logging.error(f"Failed converting column to string dtype: {e}")
                df_out[col] = s
        return df_out

    # -------------------------------------------------------------------------
    # API: list parquet DB files
    # -------------------------------------------------------------------------
    async def list_database_files(self) -> List[str]:
        prefix = (
            self.similarity_db_folder
            if self.similarity_db_folder.endswith("/")
            else f"{self.similarity_db_folder}/"
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

        files = []
        if "Contents" in response:
            for obj in response["Contents"]:
                filename = obj["Key"].split("/")[-1]
                if filename.endswith(".parquet"):
                    files.append(filename[:-8])  # strip .parquet

        return sorted(files)

    # -------------------------------------------------------------------------
    # API: load parquet database
    # -------------------------------------------------------------------------
    async def load_database_parquet(self, database_name: str) -> pd.DataFrame:
        filename = (
            database_name[:-8] if database_name.endswith(".parquet") else database_name
        )
        s3_key = (
            f"{self.similarity_db_folder}/{filename}.parquet"
            if not self.similarity_db_folder.endswith("/")
            else f"{self.similarity_db_folder}{filename}.parquet"
        )

        async with self._new_session().client(
            "s3",
            endpoint_url=self.endpoint_url,
            config=self.s3_config,
        ) as client:
            response = await client.get_object(
                Bucket=self.bucket_name,
                Key=s3_key,
            )
            file_bytes = await response["Body"].read()

        return pd.read_parquet(BytesIO(file_bytes))

    # -------------------------------------------------------------------------
    # API: upload parquet database
    # -------------------------------------------------------------------------
    async def upload_database_parquet(
        self, df: pd.DataFrame, database_name: str
    ) -> None:
        filename = (
            database_name[:-8] if database_name.endswith(".parquet") else database_name
        )
        s3_key = (
            f"{self.similarity_db_folder}/{filename}.parquet"
            if not self.similarity_db_folder.endswith("/")
            else f"{self.similarity_db_folder}{filename}.parquet"
        )

        # CPU-bound: run parquet serialization off-thread
        df_prepared = self._prepare_dataframe_for_parquet(df)

        def _to_parquet_bytes(df_local: pd.DataFrame) -> bytes:
            buffer = BytesIO()
            df_local.to_parquet(buffer, index=False, engine="pyarrow")
            return buffer.getvalue()

        parquet_bytes = await asyncio.to_thread(_to_parquet_bytes, df_prepared)

        async with self._new_session().client(
            "s3",
            endpoint_url=self.endpoint_url,
            config=self.s3_config,
        ) as client:
            await client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=parquet_bytes,
            )

    # -------------------------------------------------------------------------
    # API: get metadata
    # -------------------------------------------------------------------------
    async def get_database_metadata(self, database_name: str) -> Dict[str, Any]:
        filename = (
            database_name[:-8] if database_name.endswith(".parquet") else database_name
        )
        s3_key = (
            f"{self.similarity_db_folder}/{filename}.parquet"
            if not self.similarity_db_folder.endswith("/")
            else f"{self.similarity_db_folder}{filename}.parquet"
        )

        async with self._new_session().client(
            "s3",
            endpoint_url=self.endpoint_url,
            config=self.s3_config,
        ) as client:
            response = await client.head_object(
                Bucket=self.bucket_name,
                Key=s3_key,
            )

        return {
            "size": response.get("ContentLength", 0),
            "last_modified": response.get("LastModified"),
            "etag": response.get("ETag", "").strip('"'),
        }

    # -------------------------------------------------------------------------
    # API: list metadata for all DBs
    # -------------------------------------------------------------------------
    async def list_database_files_with_metadata(self) -> List[Dict[str, Any]]:
        prefix = (
            self.similarity_db_folder
            if self.similarity_db_folder.endswith("/")
            else f"{self.similarity_db_folder}/"
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

        files = []
        if "Contents" in response:
            for obj in response["Contents"]:
                filename = obj["Key"].split("/")[-1]
                if filename.endswith(".parquet"):
                    files.append(
                        {
                            "key": filename[:-8],
                            "size": obj.get("Size", 0),
                            "last_modified": obj.get("LastModified"),
                            "file_type": "database",
                        }
                    )

        return sorted(files, key=lambda x: x["key"])

    # -------------------------------------------------------------------------
    # API: delete database file
    # -------------------------------------------------------------------------
    async def delete_database_file(self, database_name: str) -> None:
        filename = (
            database_name[:-8] if database_name.endswith(".parquet") else database_name
        )
        s3_key = (
            f"{self.similarity_db_folder}/{filename}.parquet"
            if not self.similarity_db_folder.endswith("/")
            else f"{self.similarity_db_folder}{filename}.parquet"
        )

        async with self._new_session().client(
            "s3",
            endpoint_url=self.endpoint_url,
            config=self.s3_config,
        ) as client:
            # ensure exists (raises)
            await client.head_object(
                Bucket=self.bucket_name,
                Key=s3_key,
            )
            await client.delete_object(
                Bucket=self.bucket_name,
                Key=s3_key,
            )
