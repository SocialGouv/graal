"""
Service for loading configuration files and similarity databases from S3.

This service handles both Excel configuration files and Parquet similarity databases.
It requires S3 to be configured and does not fall back to local files.
"""

import asyncio
import logging
import logging.config
import os
import threading
from io import BytesIO
from typing import Any

import aioboto3
import boto3
import pandas as pd
from botocore.config import Config
from botocore.exceptions import ClientError, NoCredentialsError

logging.config.fileConfig("logging.conf")


class S3Service:
    """Service for loading configuration files and similarity databases from S3."""

    def __init__(self):
        """Initialize the S3 service.

        Raises:
            Exception: If S3 is not configured or not available.
        """
        self._s3_client: Any = None
        self._aioboto3_session: Any = None
        self._s3_config: Config | None = None
        self._endpoint_url: str | None = None
        self._bucket_name: str | None = None
        self._config_folder: str | None = None
        self._similarity_db_folder: str | None = None
        self._input_pool_folder: str | None = None
        self._manifest_folder: str | None = None
        self._initialize_s3()

    def _initialize_s3(self) -> None:
        """Initialize S3 client with required configuration.

        Raises:
            Exception: If S3 is not available or not properly configured.
        """

        # Check if S3 configuration environment variables are available
        required_vars = [
            "S3_BUCKET_NAME",
            "S3_BUCKET_ENDPOINT",
            "S3_BUCKET_ACCESS_KEY",
            "S3_BUCKET_SECRET_KEY",
            "S3_CONFIG_FOLDER",
            "S3_SIMILARITY_DB_FOLDER",
        ]
        missing_vars = [var for var in required_vars if not os.getenv(var)]

        if missing_vars:
            raise Exception(
                f"S3 initialization failed: Missing required environment variables: {missing_vars}"
            )

        try:
            self._endpoint_url = os.getenv("S3_BUCKET_ENDPOINT")
            self._bucket_name = os.getenv("S3_BUCKET_NAME")
            self._config_folder = os.getenv("S3_CONFIG_FOLDER")
            self._similarity_db_folder = os.getenv("S3_SIMILARITY_DB_FOLDER")
            # New environment variables with defaults
            self._input_pool_folder = os.getenv(
                "S3_INPUT_POOL_FOLDER", "input_files/pool"
            )
            self._manifest_folder = os.getenv(
                "S3_MANIFEST_FOLDER", "input_files/manifests"
            )

            # Configure timeouts and retries
            self._s3_config = Config(
                connect_timeout=int(os.getenv("S3_CONNECT_TIMEOUT", "10")),
                read_timeout=int(os.getenv("S3_READ_TIMEOUT", "60")),
                retries={
                    "max_attempts": int(os.getenv("S3_MAX_RETRIES", "3")),
                    "mode": "standard",
                },
            )

            # Initialize synchronous boto3 client
            self._s3_client = boto3.client(
                "s3",
                endpoint_url=self._endpoint_url,
                aws_access_key_id=os.getenv("S3_BUCKET_ACCESS_KEY"),
                aws_secret_access_key=os.getenv("S3_BUCKET_SECRET_KEY"),
                region_name=os.getenv("S3_BUCKET_REGION", "gra"),
                config=self._s3_config,
            )

            # Initialize aioboto3 session for async operations
            self._aioboto3_session = aioboto3.Session(
                aws_access_key_id=os.getenv("S3_BUCKET_ACCESS_KEY"),
                aws_secret_access_key=os.getenv("S3_BUCKET_SECRET_KEY"),
                region_name=os.getenv("S3_BUCKET_REGION", "gra"),
            )

            # Test connection by listing bucket (this will raise an exception if credentials are wrong)
            self._s3_client.head_bucket(Bucket=self._bucket_name)

            logging.info(
                f"S3 enabled: Connected to bucket {self._bucket_name}, "
                f"config_folder: {self._config_folder}, "
                f"similarity_db_folder: {self._similarity_db_folder}, "
                f"input_pool_folder: {self._input_pool_folder}"
            )

        except (ClientError, NoCredentialsError) as e:
            required_vars = [
                "S3_BUCKET_NAME",
                "S3_BUCKET_ENDPOINT",
                "S3_BUCKET_ACCESS_KEY",
                "S3_BUCKET_SECRET_KEY",
                "S3_CONFIG_FOLDER",
                "S3_SIMILARITY_DB_FOLDER",
            ]

            for var in required_vars:
                value = os.getenv(var)
                logging.warning(f"{var}: {value}")
            raise Exception(
                f"S3 initialization failed: Failed to initialize S3 client: {e}"
            ) from e
        except Exception as e:
            raise Exception(
                f"S3 initialization failed: Unexpected error initializing S3: {e}"
            ) from e

    def _download_from_s3(self, s3_key: str) -> BytesIO:
        """Download a file from S3 into memory.

        Args:
            s3_key: The S3 key of the file to download.

        Returns:
            BytesIO: The file content as a BytesIO object.

        Raises:
            Exception: If the download fails.
        """
        if not self._s3_client or not self._bucket_name:
            raise Exception("S3 client or bucket not configured")

        try:
            logging.info(f"Downloading file from S3: s3://{self._bucket_name}/{s3_key}")

            response = self._s3_client.get_object(Bucket=self._bucket_name, Key=s3_key)
            file_content = BytesIO(response["Body"].read())

            # Log file size
            file_size = len(file_content.getvalue())
            logging.info(f"Successfully downloaded {s3_key} ({file_size} bytes)")

            return file_content

        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "NoSuchKey":
                raise FileNotFoundError(f"File not found in S3: {s3_key}") from e
            else:
                raise Exception(f"Failed to download from S3: {e}") from e
        except Exception as e:
            raise Exception(f"Unexpected error downloading from S3: {e}") from e

    # ==================== Configuration File Methods (Synchronous) ====================

    def list_available_config_files(self) -> list[str]:
        """List all available configuration files from S3.

        Returns:
            list[str]: List of configuration file names (without paths).

        Raises:
            Exception: If S3 is not available or listing fails.
        """
        if not self._s3_client or not self._bucket_name or not self._config_folder:
            raise Exception("S3 client, bucket, or config folder not configured")

        try:
            logging.info(f"Listing configuration files from S3: {self._config_folder}/")

            # Ensure config_folder ends with / for proper prefix matching
            prefix = self._config_folder
            if not prefix.endswith("/"):
                prefix += "/"

            response = self._s3_client.list_objects_v2(
                Bucket=self._bucket_name, Prefix=prefix
            )

            files = []
            if "Contents" in response:
                for obj in response["Contents"]:
                    s3_key = obj["Key"]
                    # Extract filename from key and filter for .xlsx files
                    filename = s3_key.split("/")[-1]
                    if filename and filename.endswith(".xlsx"):
                        files.append(filename)

            logging.info(f"Found {len(files)} configuration files in S3")
            return sorted(files)

        except ClientError as e:
            error_msg = f"Failed to list configuration files from S3: {e}"
            logging.error(error_msg)
            raise Exception(error_msg) from e
        except Exception as e:
            error_msg = f"Unexpected error listing configuration files: {e}"
            logging.error(error_msg)
            raise Exception(error_msg) from e

    def validate_config_file_exists(self, filename: str) -> bool:
        """Check if a specific configuration file exists in S3.

        Args:
            filename: Name of the configuration file to check.

        Returns:
            bool: True if the file exists, False otherwise.
        """
        if not self._s3_client or not self._bucket_name or not self._config_folder:
            return False

        try:
            # Construct S3 key
            s3_key = f"{self._config_folder}/{filename}"
            if self._config_folder.endswith("/"):
                s3_key = f"{self._config_folder}{filename}"

            # Try to get object metadata
            self._s3_client.head_object(Bucket=self._bucket_name, Key=s3_key)
            logging.info(f"Configuration file exists in S3: {filename}")
            return True

        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                logging.warning(f"Configuration file not found in S3: {filename}")
                return False
            else:
                logging.error(f"Error checking file existence: {e}")
                return False
        except Exception as e:
            logging.error(f"Unexpected error checking file existence: {e}")
            return False

    def load_config_excel(self, filename: str) -> dict[str, pd.DataFrame]:
        """Load a configuration Excel file from S3.

        Args:
            filename: Name of the Excel file (e.g., "Fichier de configuration GRAAL - DSS - latest.xlsx")

        Returns:
            dict[str, pd.DataFrame]: Dictionary mapping sheet names to DataFrames.

        Raises:
            FileNotFoundError: If the file is not found in S3.
            Exception: If there's an error loading the file.
        """
        if not self._config_folder:
            raise Exception("S3 config folder not configured")

        logging.info(f"Loading configuration file from S3: {filename}")

        # Construct S3 key
        s3_key = f"{self._config_folder}/{filename}"
        if self._config_folder.endswith("/"):
            s3_key = f"{self._config_folder}{filename}"

        try:
            file_content = self._download_from_s3(s3_key)
            excel_data = pd.read_excel(file_content, sheet_name=None)
            logging.info(
                f"Loaded configuration from S3 - filename: {filename}, sheets: {list(excel_data.keys())}"
            )
            return excel_data
        except FileNotFoundError:
            # Re-raise FileNotFoundError as-is
            raise
        except Exception as e:
            error_msg = f"Failed to load configuration file '{filename}' from S3: {e}"
            logging.error(error_msg)
            raise Exception(error_msg) from e

    def list_config_files_with_metadata(self) -> list[dict[str, Any]]:
        """List all configuration files with detailed metadata.

        Returns:
            list[dict[str, Any]]: List of dicts with {key, size, last_modified, file_type}

        Raises:
            Exception: If S3 is not available or listing fails.
        """
        if not self._s3_client or not self._bucket_name or not self._config_folder:
            raise Exception("S3 client, bucket, or config folder not configured")

        try:
            logging.info(
                f"Listing configuration files with metadata from S3: {self._config_folder}/"
            )

            # Ensure config_folder ends with / for proper prefix matching
            prefix = self._config_folder
            if not prefix.endswith("/"):
                prefix += "/"

            response = self._s3_client.list_objects_v2(
                Bucket=self._bucket_name, Prefix=prefix
            )

            files = []
            if "Contents" in response:
                for obj in response["Contents"]:
                    s3_key = obj["Key"]
                    # Extract filename from key and filter for .xlsx files
                    filename = s3_key.split("/")[-1]
                    if filename and filename.endswith(".xlsx"):
                        files.append(
                            {
                                "key": filename,
                                "size": obj.get("Size", 0),
                                "last_modified": obj.get("LastModified"),
                                "file_type": "config",
                            }
                        )

            logging.info(f"Found {len(files)} configuration files with metadata in S3")
            return sorted(files, key=lambda x: x["key"])

        except ClientError as e:
            error_msg = f"Failed to list configuration files with metadata from S3: {e}"
            logging.error(error_msg)
            raise Exception(error_msg) from e
        except Exception as e:
            error_msg = (
                f"Unexpected error listing configuration files with metadata: {e}"
            )
            logging.error(error_msg)
            raise Exception(error_msg) from e

    def delete_config_file(self, filename: str) -> None:
        """Delete a configuration file from S3.

        Args:
            filename: Name of the configuration file to delete.

        Raises:
            FileNotFoundError: If the file is not found in S3.
            Exception: If deletion fails.
        """
        if not self._s3_client or not self._bucket_name or not self._config_folder:
            raise Exception("S3 client, bucket, or config folder not configured")

        try:
            # Construct S3 key
            s3_key = f"{self._config_folder}/{filename}"
            if self._config_folder.endswith("/"):
                s3_key = f"{self._config_folder}{filename}"

            logging.info(
                f"Deleting configuration file from S3: s3://{self._bucket_name}/{s3_key}"
            )

            # First check if file exists
            if not self.validate_config_file_exists(filename):
                raise FileNotFoundError(
                    f"Configuration file not found in S3: {filename}"
                )

            # Delete the file
            self._s3_client.delete_object(Bucket=self._bucket_name, Key=s3_key)

            logging.info(f"Successfully deleted configuration file: {filename}")

        except FileNotFoundError:
            # Re-raise FileNotFoundError as-is
            raise
        except ClientError as e:
            error_msg = f"Failed to delete configuration file '{filename}' from S3: {e}"
            logging.error(error_msg)
            raise Exception(error_msg) from e
        except Exception as e:
            error_msg = (
                f"Unexpected error deleting configuration file '{filename}': {e}"
            )
            logging.error(error_msg)
            raise Exception(error_msg) from e

    # ==================== Similarity Database Methods (Asynchronous) ====================

    async def list_database_files(self) -> list[str]:
        """List available similarity database parquet files from S3_SIMILARITY_DB_FOLDER.

        Returns:
            list[str]: List of database names (filenames without .parquet extension).

        Raises:
            Exception: If S3 is not available or listing fails.
        """
        if (
            not self._aioboto3_session
            or not self._bucket_name
            or not self._similarity_db_folder
        ):
            raise Exception(
                "S3 session, bucket, or similarity DB folder not configured"
            )

        try:
            logging.info(
                f"Listing similarity database files from S3: {self._similarity_db_folder}/"
            )

            # Ensure similarity_db_folder ends with / for proper prefix matching
            prefix = self._similarity_db_folder
            if not prefix.endswith("/"):
                prefix += "/"

            async with self._aioboto3_session.client(
                "s3",
                endpoint_url=self._endpoint_url,
                config=self._s3_config,
            ) as s3_client:
                response = await s3_client.list_objects_v2(
                    Bucket=self._bucket_name, Prefix=prefix
                )

                files = []
                if "Contents" in response:
                    for obj in response["Contents"]:
                        s3_key = obj["Key"]
                        # Extract filename from key and filter for .parquet files
                        filename = s3_key.split("/")[-1]
                        if filename and filename.endswith(".parquet"):
                            # Remove .parquet extension
                            database_name = filename[:-8]
                            files.append(database_name)

                logging.info(f"Found {len(files)} similarity database files in S3")
                return sorted(files)

        except ClientError as e:
            error_msg = f"Failed to list similarity database files from S3: {e}"
            logging.error(error_msg)
            raise Exception(error_msg) from e
        except Exception as e:
            error_msg = f"Unexpected error listing similarity database files: {e}"
            logging.error(error_msg)
            raise Exception(error_msg) from e

    async def load_database_parquet(self, database_name: str) -> pd.DataFrame:
        """Load a similarity database parquet file from S3.

        Args:
            database_name: Name of database (with or without .parquet extension)

        Returns:
            pd.DataFrame: DataFrame with similarity database content

        Raises:
            FileNotFoundError: If the file is not found in S3.
            Exception: If there's an error loading the file.
        """
        if (
            not self._aioboto3_session
            or not self._bucket_name
            or not self._similarity_db_folder
        ):
            raise Exception(
                "S3 session, bucket, or similarity DB folder not configured"
            )

        logging.info(f"Loading similarity database from S3: {database_name}")

        # Strip .parquet extension if already present to avoid double extension
        database_name_clean = (
            database_name.rstrip(".parquet")
            if database_name.endswith(".parquet")
            else database_name
        )

        # Construct S3 key with .parquet extension
        s3_key = f"{self._similarity_db_folder}/{database_name_clean}.parquet"
        if self._similarity_db_folder.endswith("/"):
            s3_key = f"{self._similarity_db_folder}{database_name_clean}.parquet"

        try:
            logging.info(
                f"Downloading database file from S3: s3://{self._bucket_name}/{s3_key}"
            )

            async with self._aioboto3_session.client(
                "s3",
                endpoint_url=self._endpoint_url,
                config=self._s3_config,
            ) as s3_client:
                response = await s3_client.get_object(
                    Bucket=self._bucket_name, Key=s3_key
                )

                # Read the streaming body
                file_bytes = await response["Body"].read()
                file_size = len(file_bytes)
                logging.info(f"Successfully downloaded {s3_key} ({file_size} bytes)")

                # Load parquet from bytes
                file_content = BytesIO(file_bytes)
                df = pd.read_parquet(file_content)
                logging.info(
                    f"Loaded similarity database from S3 - database: {database_name}, "
                    f"rows: {len(df)}, columns: {list(df.columns)}"
                )
                return df

        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "NoSuchKey":
                raise FileNotFoundError(
                    f"Similarity database not found in S3: {database_name}"
                ) from e
            else:
                raise Exception(f"Failed to download database from S3: {e}") from e
        except Exception as e:
            error_msg = (
                f"Failed to load similarity database '{database_name}' from S3: {e}"
            )
            logging.error(error_msg)
            raise Exception(error_msg) from e

    def _prepare_dataframe_for_parquet(self, df: pd.DataFrame) -> pd.DataFrame:
        """Sanitize DataFrame to ensure Arrow-compatible column types.

        - Convert object columns with bytes/mixed types to string dtype
        - Decode bytes/bytearray as UTF-8 (replace errors)
        - Preserve NaN/None as nulls
        """
        df_out = df.copy()

        for col in df_out.columns:
            s = df_out[col]
            # Only coerce problematic object columns
            if s.dtype == "object":
                # Decode bytes to str first if present
                if (
                    getattr(s, "apply", None)
                    and s.apply(lambda v: isinstance(v, (bytes, bytearray))).any()
                ):
                    s = s.apply(
                        lambda v: v.decode("utf-8", "replace")
                        if isinstance(v, (bytes, bytearray))
                        else v
                    )
                # If not a pure string dtype, map everything to string while preserving nulls
                import pandas as _pd  # local alias to avoid overshadow

                if not _pd.api.types.is_string_dtype(s):
                    s = s.map(lambda v: (None if _pd.isna(v) else str(v)))
                # Use pandas nullable string dtype for better Arrow compatibility
                try:
                    s = s.astype("string")
                except Exception as e:
                    # Fallback: keep as object if conversion fails
                    logging.error(f"Failed to convert column to string dtype: {e}")
                df_out[col] = s
        return df_out

    async def upload_database_parquet(
        self, df: pd.DataFrame, database_name: str
    ) -> None:
        """Upload a similarity database to S3 as parquet (async).

        Args:
            df: DataFrame to upload
            database_name: Name for the database (without .parquet extension)
        """
        if (
            not self._aioboto3_session
            or not self._bucket_name
            or not self._similarity_db_folder
        ):
            raise Exception(
                "S3 session, bucket, or similarity DB folder not configured"
            )

        logging.info(f"Uploading similarity database to S3: {database_name}")

        # Construct S3 key with .parquet extension
        s3_key = f"{self._similarity_db_folder}/{database_name}.parquet"
        if self._similarity_db_folder.endswith("/"):
            s3_key = f"{self._similarity_db_folder}{database_name}.parquet"

        try:
            # Serialize DataFrame to parquet bytes off the event loop (CPU-bound)
            def _to_parquet_bytes(df_local: pd.DataFrame) -> bytes:
                buffer = BytesIO()
                df_local.to_parquet(buffer, index=False, engine="pyarrow")
                return buffer.getvalue()

            df_prepared = self._prepare_dataframe_for_parquet(df)
            parquet_bytes: bytes = await asyncio.to_thread(
                _to_parquet_bytes, df_prepared
            )
            file_size = len(parquet_bytes)

            logging.info(
                f"Uploading database file to S3: s3://{self._bucket_name}/{s3_key} ({file_size} bytes)"
            )

            async with self._aioboto3_session.client(
                "s3",
                endpoint_url=self._endpoint_url,
                config=self._s3_config,
            ) as s3_client:
                await s3_client.put_object(
                    Bucket=self._bucket_name,
                    Key=s3_key,
                    Body=parquet_bytes,
                )

            logging.info(
                f"Successfully uploaded similarity database to S3 - database: {database_name}, "
                f"rows: {len(df)}, size: {file_size} bytes"
            )

        except Exception as e:
            # Provide a helpful hint if parquet engine is missing
            msg = str(e)
            if "pyarrow" in msg or "fastparquet" in msg or "parquet" in msg.lower():
                hint = " Ensure a parquet engine is installed (e.g., add 'pyarrow' to your environment)."
            else:
                hint = ""
            error_msg = f"Failed to upload similarity database '{database_name}' to S3: {e}.{hint}"
            logging.error(error_msg)
            raise Exception(error_msg) from e

    async def get_database_metadata(self, database_name: str) -> dict[str, Any]:
        """Get metadata about a database file (size, last modified, etc.)

        Args:
            database_name: Name of database (without .parquet extension)

        Returns:
            dict[str, Any]: Dictionary with metadata (size, last_modified, etag)

        Raises:
            FileNotFoundError: If the file is not found in S3.
            Exception: If there's an error getting metadata.
        """
        if (
            not self._aioboto3_session
            or not self._bucket_name
            or not self._similarity_db_folder
        ):
            raise Exception(
                "S3 session, bucket, or similarity DB folder not configured"
            )

        # Construct S3 key with .parquet extension
        s3_key = f"{self._similarity_db_folder}/{database_name}.parquet"
        if self._similarity_db_folder.endswith("/"):
            s3_key = f"{self._similarity_db_folder}{database_name}.parquet"

        try:
            logging.info(f"Getting metadata for database: {database_name}")

            async with self._aioboto3_session.client(
                "s3",
                endpoint_url=self._endpoint_url,
                config=self._s3_config,
            ) as s3_client:
                response = await s3_client.head_object(
                    Bucket=self._bucket_name, Key=s3_key
                )

                metadata = {
                    "size": response.get("ContentLength", 0),
                    "last_modified": response.get("LastModified"),
                    "etag": response.get("ETag", "").strip('"'),
                }

                logging.info(
                    f"Database metadata - {database_name}: size={metadata['size']} bytes, "
                    f"last_modified={metadata['last_modified']}"
                )
                return metadata

        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                raise FileNotFoundError(
                    f"Similarity database not found in S3: {database_name}.parquet"
                ) from e
            else:
                raise Exception(f"Failed to get database metadata from S3: {e}") from e
        except Exception as e:
            error_msg = (
                f"Failed to get metadata for database '{database_name}' from S3: {e}"
            )
            logging.error(error_msg)
            raise Exception(error_msg) from e

    async def list_database_files_with_metadata(self) -> list[dict[str, Any]]:
        """List similarity database files with detailed metadata.

        Returns:
            list[dict[str, Any]]: List of dicts with {key, size, last_modified, file_type}

        Raises:
            Exception: If S3 is not available or listing fails.
        """
        if (
            not self._aioboto3_session
            or not self._bucket_name
            or not self._similarity_db_folder
        ):
            raise Exception(
                "S3 session, bucket, or similarity DB folder not configured"
            )

        try:
            logging.info(
                f"Listing similarity database files with metadata from S3: {self._similarity_db_folder}/"
            )

            # Ensure similarity_db_folder ends with / for proper prefix matching
            prefix = self._similarity_db_folder
            if not prefix.endswith("/"):
                prefix += "/"

            async with self._aioboto3_session.client(
                "s3",
                endpoint_url=self._endpoint_url,
                config=self._s3_config,
            ) as s3_client:
                response = await s3_client.list_objects_v2(
                    Bucket=self._bucket_name, Prefix=prefix
                )

                files = []
                if "Contents" in response:
                    for obj in response["Contents"]:
                        s3_key = obj["Key"]
                        # Extract filename from key and filter for .parquet files
                        filename = s3_key.split("/")[-1]
                        if filename and filename.endswith(".parquet"):
                            # Remove .parquet extension for display
                            database_name = filename[:-8]
                            files.append(
                                {
                                    "key": database_name,
                                    "size": obj.get("Size", 0),
                                    "last_modified": obj.get("LastModified"),
                                    "file_type": "database",
                                }
                            )

                logging.info(
                    f"Found {len(files)} similarity database files with metadata in S3"
                )
                return sorted(files, key=lambda x: x["key"])

        except ClientError as e:
            error_msg = (
                f"Failed to list similarity database files with metadata from S3: {e}"
            )
            logging.error(error_msg)
            raise Exception(error_msg) from e
        except Exception as e:
            error_msg = (
                f"Unexpected error listing similarity database files with metadata: {e}"
            )
            logging.error(error_msg)
            raise Exception(error_msg) from e

    async def delete_database_file(self, database_name: str) -> None:
        """Delete a similarity database file from S3.

        Args:
            database_name: Name of database (without .parquet extension)

        Raises:
            FileNotFoundError: If the file is not found in S3.
            Exception: If deletion fails.
        """
        if (
            not self._aioboto3_session
            or not self._bucket_name
            or not self._similarity_db_folder
        ):
            raise Exception(
                "S3 session, bucket, or similarity DB folder not configured"
            )

        try:
            # Strip .parquet extension if already present to avoid double extension
            database_name_clean = (
                database_name.rstrip(".parquet")
                if database_name.endswith(".parquet")
                else database_name
            )

            # Construct S3 key with .parquet extension
            s3_key = f"{self._similarity_db_folder}/{database_name_clean}.parquet"
            if self._similarity_db_folder.endswith("/"):
                s3_key = f"{self._similarity_db_folder}{database_name_clean}.parquet"

            logging.info(
                f"Deleting similarity database from S3: s3://{self._bucket_name}/{s3_key}"
            )

            async with self._aioboto3_session.client(
                "s3",
                endpoint_url=self._endpoint_url,
                config=self._s3_config,
            ) as s3_client:
                # First check if file exists
                try:
                    await s3_client.head_object(Bucket=self._bucket_name, Key=s3_key)
                except ClientError as e:
                    if e.response["Error"]["Code"] == "404":
                        raise FileNotFoundError(
                            f"Similarity database not found in S3: {database_name}"
                        ) from e
                    raise

                # Delete the file
                await s3_client.delete_object(Bucket=self._bucket_name, Key=s3_key)

            logging.info(f"Successfully deleted similarity database: {database_name}")

        except FileNotFoundError:
            # Re-raise FileNotFoundError as-is
            raise
        except ClientError as e:
            error_msg = (
                f"Failed to delete similarity database '{database_name}' from S3: {e}"
            )
            logging.error(error_msg)
            raise Exception(error_msg) from e
        except Exception as e:
            error_msg = (
                f"Unexpected error deleting similarity database '{database_name}': {e}"
            )
            logging.error(error_msg)
            raise Exception(error_msg) from e

    # ==================== Input File Pool Methods (Asynchronous) ====================

    async def upload_to_input_pool(self, file_content: bytes, s3_key: str) -> None:
        """Upload file to input file pool.

        Args:
            file_content: The file content as bytes to upload.
            s3_key: The S3 key (filename with hash) for the file in the pool.

        Raises:
            Exception: If upload fails.
        """
        if (
            not self._aioboto3_session
            or not self._bucket_name
            or not self._input_pool_folder
        ):
            raise Exception("S3 session, bucket, or input pool folder not configured")

        logging.info(f"Uploading file to input pool: {s3_key}")

        # Construct full S3 key with pool folder prefix
        full_s3_key = f"{self._input_pool_folder}/{s3_key}"
        if self._input_pool_folder.endswith("/"):
            full_s3_key = f"{self._input_pool_folder}{s3_key}"

        try:
            file_size = len(file_content)
            logging.info(
                f"Uploading to input pool: s3://{self._bucket_name}/{full_s3_key} ({file_size} bytes)"
            )

            async with self._aioboto3_session.client(
                "s3",
                endpoint_url=self._endpoint_url,
                config=self._s3_config,
            ) as s3_client:
                await s3_client.put_object(
                    Bucket=self._bucket_name,
                    Key=full_s3_key,
                    Body=file_content,
                )

            logging.info(
                f"Successfully uploaded to input pool - key: {s3_key}, size: {file_size} bytes"
            )

        except Exception as e:
            error_msg = f"Failed to upload file to input pool '{s3_key}': {e}"
            logging.error(error_msg)
            raise Exception(error_msg) from e

    async def download_from_input_pool(self, s3_key: str) -> bytes:
        """Download file from input file pool.

        Args:
            s3_key: The S3 key (filename with hash) for the file in the pool.

        Returns:
            bytes: The file content as bytes.

        Raises:
            FileNotFoundError: If the file is not found in S3.
            Exception: If download fails.
        """
        if (
            not self._aioboto3_session
            or not self._bucket_name
            or not self._input_pool_folder
        ):
            raise Exception("S3 session, bucket, or input pool folder not configured")

        logging.info(f"Downloading file from input pool: {s3_key}")

        # Construct full S3 key with pool folder prefix
        full_s3_key = f"{self._input_pool_folder}/{s3_key}"
        if self._input_pool_folder.endswith("/"):
            full_s3_key = f"{self._input_pool_folder}{s3_key}"

        try:
            logging.info(
                f"Downloading from input pool: s3://{self._bucket_name}/{full_s3_key}"
            )

            async with self._aioboto3_session.client(
                "s3",
                endpoint_url=self._endpoint_url,
                config=self._s3_config,
            ) as s3_client:
                response = await s3_client.get_object(
                    Bucket=self._bucket_name, Key=full_s3_key
                )

                # Read the streaming body
                file_bytes = await response["Body"].read()
                file_size = len(file_bytes)
                logging.info(
                    f"Successfully downloaded from input pool - key: {s3_key}, size: {file_size} bytes"
                )

                return file_bytes

        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "NoSuchKey":
                raise FileNotFoundError(
                    f"File not found in input pool: {s3_key}"
                ) from e
            else:
                raise Exception(f"Failed to download from input pool: {e}") from e
        except Exception as e:
            error_msg = f"Failed to download file from input pool '{s3_key}': {e}"
            logging.error(error_msg)
            raise Exception(error_msg) from e

    async def list_pool_files_by_hash_prefix(self, file_hash: str) -> list[str]:
        """List all files in input pool matching a hash prefix.

        This is useful for finding files when you only know the hash but not the extension.

        Args:
            file_hash: SHA256 hash of the file (without extension).

        Returns:
            list[str]: List of S3 keys (relative to pool folder) matching the hash prefix.
        """
        if (
            not self._aioboto3_session
            or not self._bucket_name
            or not self._input_pool_folder
        ):
            return []

        # Construct prefix to search for files with this hash
        prefix = f"{self._input_pool_folder}/{file_hash}"
        if self._input_pool_folder.endswith("/"):
            prefix = f"{self._input_pool_folder}{file_hash}"

        try:
            logging.debug(f"Listing files in input pool with hash prefix: {file_hash}")

            async with self._aioboto3_session.client(
                "s3",
                endpoint_url=self._endpoint_url,
                config=self._s3_config,
            ) as s3_client:
                response = await s3_client.list_objects_v2(
                    Bucket=self._bucket_name, Prefix=prefix, MaxKeys=10
                )

                files = []
                if "Contents" in response:
                    for obj in response["Contents"]:
                        # Extract the key relative to the pool folder
                        full_key = obj["Key"]
                        # Remove the pool folder prefix
                        if full_key.startswith(f"{self._input_pool_folder}/"):
                            relative_key = full_key[len(self._input_pool_folder) + 1 :]
                        elif full_key.startswith(self._input_pool_folder):
                            relative_key = full_key[len(self._input_pool_folder) :]
                        else:
                            relative_key = full_key
                        files.append(relative_key)

                logging.debug(
                    f"Found {len(files)} files in input pool with hash {file_hash}"
                )
                return files

        except Exception as e:
            logging.error(f"Error listing files by hash prefix in pool: {e}")
            return []

    async def get_input_pool_metadata(self, s3_key: str) -> dict[str, Any]:
        """Get metadata for file in input pool.

        Args:
            s3_key: The S3 key (filename with hash) for the file in the pool.

        Returns:
            dict: Metadata including size, last_modified, content_type, etc.

        Raises:
            FileNotFoundError: If file doesn't exist in pool.
            Exception: If metadata retrieval fails.
        """
        if (
            not self._aioboto3_session
            or not self._bucket_name
            or not self._input_pool_folder
        ):
            raise Exception("S3 session, bucket, or input pool folder not configured")

        logging.debug(f"Getting metadata for file in input pool: {s3_key}")

        # Construct full S3 key with pool folder prefix
        full_s3_key = f"{self._input_pool_folder}/{s3_key}"
        if self._input_pool_folder.endswith("/"):
            full_s3_key = f"{self._input_pool_folder}{s3_key}"

        try:
            async with self._aioboto3_session.client(
                "s3",
                endpoint_url=self._endpoint_url,
                config=self._s3_config,
            ) as s3_client:
                response = await s3_client.head_object(
                    Bucket=self._bucket_name, Key=full_s3_key
                )

                metadata = {
                    "size": response.get("ContentLength", 0),
                    "last_modified": response.get("LastModified"),
                    "content_type": response.get("ContentType"),
                    "etag": response.get("ETag", "").strip('"'),
                }

                logging.debug(f"Retrieved metadata for {s3_key}: {metadata}")
                return metadata

        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "404":
                raise FileNotFoundError(f"File not found in pool: {s3_key}") from e
            else:
                raise Exception(f"Failed to get file metadata from pool: {e}") from e
        except Exception as e:
            error_msg = f"Unexpected error getting metadata from pool ({s3_key}): {e}"
            logging.error(error_msg)
            raise Exception(error_msg) from e

    async def file_exists_in_pool(self, s3_key: str) -> bool:
        """Check if file exists in input pool.

        Args:
            s3_key: The S3 key (filename with hash) for the file in the pool.

        Returns:
            bool: True if the file exists, False otherwise.
        """
        if (
            not self._aioboto3_session
            or not self._bucket_name
            or not self._input_pool_folder
        ):
            return False

        # Construct full S3 key with pool folder prefix
        full_s3_key = f"{self._input_pool_folder}/{s3_key}"
        if self._input_pool_folder.endswith("/"):
            full_s3_key = f"{self._input_pool_folder}{s3_key}"

        try:
            logging.info(f"Checking if file exists in input pool: {s3_key}")

            async with self._aioboto3_session.client(
                "s3",
                endpoint_url=self._endpoint_url,
                config=self._s3_config,
            ) as s3_client:
                await s3_client.head_object(Bucket=self._bucket_name, Key=full_s3_key)

            logging.info(f"File exists in input pool: {s3_key}")
            return True

        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                logging.info(f"File not found in input pool: {s3_key}")
                return False
            else:
                logging.error(f"Error checking file existence in pool: {e}")
                return False
        except Exception as e:
            logging.error(f"Unexpected error checking file existence in pool: {e}")
            return False

    async def list_input_pool_files_with_metadata(self) -> list[dict[str, Any]]:
        """List all files in input pool with detailed metadata.

        Returns:
            list[dict[str, Any]]: List of dicts with {key, size, last_modified, file_type}

        Raises:
            Exception: If S3 is not available or listing fails.
        """
        if (
            not self._aioboto3_session
            or not self._bucket_name
            or not self._input_pool_folder
        ):
            raise Exception("S3 session, bucket, or input pool folder not configured")

        try:
            logging.info(
                f"Listing input pool files with metadata from S3: {self._input_pool_folder}/"
            )

            # Ensure input_pool_folder ends with / for proper prefix matching
            prefix = self._input_pool_folder
            if not prefix.endswith("/"):
                prefix += "/"

            async with self._aioboto3_session.client(
                "s3",
                endpoint_url=self._endpoint_url,
                config=self._s3_config,
            ) as s3_client:
                response = await s3_client.list_objects_v2(
                    Bucket=self._bucket_name, Prefix=prefix
                )

                files = []
                if "Contents" in response:
                    for obj in response["Contents"]:
                        full_key = obj["Key"]
                        # Extract relative key (remove pool folder prefix)
                        if full_key.startswith(f"{self._input_pool_folder}/"):
                            relative_key = full_key[len(self._input_pool_folder) + 1 :]
                        elif full_key.startswith(self._input_pool_folder):
                            relative_key = full_key[len(self._input_pool_folder) :]
                        else:
                            relative_key = full_key

                        # Skip empty keys (folders)
                        if relative_key:
                            files.append(
                                {
                                    "key": relative_key,
                                    "size": obj.get("Size", 0),
                                    "last_modified": obj.get("LastModified"),
                                    "file_type": "input_file",
                                }
                            )

                logging.info(f"Found {len(files)} input pool files with metadata in S3")
                return sorted(files, key=lambda x: x["key"])

        except ClientError as e:
            error_msg = f"Failed to list input pool files with metadata from S3: {e}"
            logging.error(error_msg)
            raise Exception(error_msg) from e
        except Exception as e:
            error_msg = f"Unexpected error listing input pool files with metadata: {e}"
            logging.error(error_msg)
            raise Exception(error_msg) from e

    async def delete_input_pool_file(self, s3_key: str) -> None:
        """Delete a file from input pool.

        Args:
            s3_key: The S3 key (relative to pool folder) of the file to delete.

        Raises:
            FileNotFoundError: If the file is not found in S3.
            Exception: If deletion fails.
        """
        if (
            not self._aioboto3_session
            or not self._bucket_name
            or not self._input_pool_folder
        ):
            raise Exception("S3 session, bucket, or input pool folder not configured")

        try:
            # Construct full S3 key with pool folder prefix
            full_s3_key = f"{self._input_pool_folder}/{s3_key}"
            if self._input_pool_folder.endswith("/"):
                full_s3_key = f"{self._input_pool_folder}{s3_key}"

            logging.info(
                f"Deleting file from input pool: s3://{self._bucket_name}/{full_s3_key}"
            )

            async with self._aioboto3_session.client(
                "s3",
                endpoint_url=self._endpoint_url,
                config=self._s3_config,
            ) as s3_client:
                # First check if file exists
                try:
                    await s3_client.head_object(
                        Bucket=self._bucket_name, Key=full_s3_key
                    )
                except ClientError as e:
                    if e.response["Error"]["Code"] == "404":
                        raise FileNotFoundError(
                            f"File not found in input pool: {s3_key}"
                        ) from e
                    raise

                # Delete the file
                await s3_client.delete_object(Bucket=self._bucket_name, Key=full_s3_key)

            logging.info(f"Successfully deleted file from input pool: {s3_key}")

        except FileNotFoundError:
            # Re-raise FileNotFoundError as-is
            raise
        except ClientError as e:
            error_msg = f"Failed to delete file from input pool '{s3_key}': {e}"
            logging.error(error_msg)
            raise Exception(error_msg) from e
        except Exception as e:
            error_msg = (
                f"Unexpected error deleting file from input pool '{s3_key}': {e}"
            )
            logging.error(error_msg)
            raise Exception(error_msg) from e

    # ==================== Manifest Methods (Asynchronous) ====================

    async def upload_manifest(self, database_name: str, manifest_data: dict) -> None:
        """Upload database manifest as JSON.

        Args:
            database_name: Name of the database.
            manifest_data: Dictionary containing manifest data to upload.

        Raises:
            Exception: If upload fails.
        """
        if (
            not self._aioboto3_session
            or not self._bucket_name
            or not self._manifest_folder
        ):
            raise Exception("S3 session, bucket, or manifest folder not configured")

        logging.info(f"Uploading manifest for database: {database_name}")

        # Construct S3 key with manifest folder prefix and .json extension
        s3_key = f"{self._manifest_folder}/{database_name}.json"
        if self._manifest_folder.endswith("/"):
            s3_key = f"{self._manifest_folder}{database_name}.json"

        try:
            import json

            # Serialize manifest to JSON
            manifest_json = json.dumps(manifest_data, indent=2, default=str)
            manifest_bytes = manifest_json.encode("utf-8")
            file_size = len(manifest_bytes)

            logging.info(
                f"Uploading manifest to S3: s3://{self._bucket_name}/{s3_key} ({file_size} bytes)"
            )

            async with self._aioboto3_session.client(
                "s3",
                endpoint_url=self._endpoint_url,
                config=self._s3_config,
            ) as s3_client:
                await s3_client.put_object(
                    Bucket=self._bucket_name,
                    Key=s3_key,
                    Body=manifest_bytes,
                    ContentType="application/json",
                )

            logging.info(
                f"Successfully uploaded manifest - database: {database_name}, size: {file_size} bytes"
            )

        except Exception as e:
            error_msg = f"Failed to upload manifest for database '{database_name}': {e}"
            logging.error(error_msg)
            raise Exception(error_msg) from e

    async def download_manifest(self, database_name: str) -> dict:
        """Download and parse database manifest.

        Args:
            database_name: Name of the database.

        Returns:
            dict: Parsed manifest data.

        Raises:
            FileNotFoundError: If the manifest is not found in S3.
            Exception: If download or parsing fails.
        """
        if (
            not self._aioboto3_session
            or not self._bucket_name
            or not self._manifest_folder
        ):
            raise Exception("S3 session, bucket, or manifest folder not configured")

        logging.info(f"Downloading manifest for database: {database_name}")

        # Construct S3 key with manifest folder prefix and .json extension
        s3_key = f"{self._manifest_folder}/{database_name}.json"
        if self._manifest_folder.endswith("/"):
            s3_key = f"{self._manifest_folder}{database_name}.json"

        try:
            logging.info(
                f"Downloading manifest from S3: s3://{self._bucket_name}/{s3_key}"
            )

            async with self._aioboto3_session.client(
                "s3",
                endpoint_url=self._endpoint_url,
                config=self._s3_config,
            ) as s3_client:
                response = await s3_client.get_object(
                    Bucket=self._bucket_name, Key=s3_key
                )

                # Read the streaming body
                manifest_bytes = await response["Body"].read()
                file_size = len(manifest_bytes)
                logging.info(
                    f"Successfully downloaded manifest - database: {database_name}, size: {file_size} bytes"
                )

                # Parse JSON
                import json

                manifest_data = json.loads(manifest_bytes.decode("utf-8"))
                logging.info(
                    f"Successfully parsed manifest for database: {database_name}"
                )

                return manifest_data

        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "NoSuchKey":
                raise FileNotFoundError(
                    f"Manifest not found for database: {database_name}"
                ) from e
            else:
                raise Exception(f"Failed to download manifest from S3: {e}") from e
        except json.JSONDecodeError as e:
            error_msg = (
                f"Failed to parse manifest JSON for database '{database_name}': {e}"
            )
            logging.error(error_msg)
            raise Exception(error_msg) from e
        except Exception as e:
            error_msg = (
                f"Failed to download manifest for database '{database_name}': {e}"
            )
            logging.error(error_msg)
            raise Exception(error_msg) from e

    async def manifest_exists(self, database_name: str) -> bool:
        """Check if manifest exists for database.

        Args:
            database_name: Name of the database.

        Returns:
            bool: True if the manifest exists, False otherwise.
        """
        if (
            not self._aioboto3_session
            or not self._bucket_name
            or not self._manifest_folder
        ):
            return False

        # Construct S3 key with manifest folder prefix and .json extension
        s3_key = f"{self._manifest_folder}/{database_name}.json"
        if self._manifest_folder.endswith("/"):
            s3_key = f"{self._manifest_folder}{database_name}.json"

        try:
            logging.info(f"Checking if manifest exists for database: {database_name}")

            async with self._aioboto3_session.client(
                "s3",
                endpoint_url=self._endpoint_url,
                config=self._s3_config,
            ) as s3_client:
                await s3_client.head_object(Bucket=self._bucket_name, Key=s3_key)

            logging.info(f"Manifest exists for database: {database_name}")
            return True

        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                logging.info(f"Manifest not found for database: {database_name}")
                return False
            else:
                logging.error(f"Error checking manifest existence: {e}")
                return False
        except Exception as e:
            logging.error(f"Unexpected error checking manifest existence: {e}")
            return False

    async def delete_manifest(self, database_name: str) -> None:
        """Delete database manifest.

        Args:
            database_name: Name of the database.

        Raises:
            FileNotFoundError: If the manifest is not found in S3.
            Exception: If deletion fails.
        """
        if (
            not self._aioboto3_session
            or not self._bucket_name
            or not self._manifest_folder
        ):
            raise Exception("S3 session, bucket, or manifest folder not configured")

        logging.info(f"Deleting manifest for database: {database_name}")

        # Construct S3 key with manifest folder prefix and .json extension
        s3_key = f"{self._manifest_folder}/{database_name}.json"
        if self._manifest_folder.endswith("/"):
            s3_key = f"{self._manifest_folder}{database_name}.json"

        try:
            # First check if the manifest exists
            exists = await self.manifest_exists(database_name)
            if not exists:
                raise FileNotFoundError(
                    f"Manifest not found for database: {database_name}"
                )

            logging.info(
                f"Deleting manifest from S3: s3://{self._bucket_name}/{s3_key}"
            )

            async with self._aioboto3_session.client(
                "s3",
                endpoint_url=self._endpoint_url,
                config=self._s3_config,
            ) as s3_client:
                await s3_client.delete_object(Bucket=self._bucket_name, Key=s3_key)

            logging.info(f"Successfully deleted manifest for database: {database_name}")

        except FileNotFoundError:
            # Re-raise FileNotFoundError as-is
            raise
        except Exception as e:
            error_msg = f"Failed to delete manifest for database '{database_name}': {e}"
            logging.error(error_msg)
            raise Exception(error_msg) from e


# Global singleton instance
_s3_service: S3Service | None = None
_lock = threading.Lock()


def get_s3_service() -> S3Service:
    """Get the global S3Service singleton instance.

    Returns:
        S3Service: The global S3 service instance.
    """
    global _s3_service
    if _s3_service is None:
        with _lock:
            if _s3_service is None:
                _s3_service = S3Service()
                logging.info("Initialized S3Service singleton")
    return _s3_service
