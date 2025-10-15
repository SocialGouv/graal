"""
Service for loading configuration files from S3.

This service requires S3 to be configured and does not fall back to local files.
"""

import logging
import os
from io import BytesIO
from typing import Any

import boto3
import pandas as pd
from botocore.exceptions import ClientError, NoCredentialsError

logger = logging.getLogger(__name__)


class S3ConfigService:
    """Service for loading configuration files from S3."""

    def __init__(self):
        """Initialize the S3 config service.

        Raises:
            Exception: If S3 is not configured or not available.
        """
        self._s3_client: Any = None
        self._bucket_name: str | None = None
        self._office_directories: str | None = None
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
        ]
        missing_vars = [var for var in required_vars if not os.getenv(var)]

        if missing_vars:
            raise Exception(
                f"S3 initialization failed: Missing required environment variables: {missing_vars}"
            )

        try:
            self._bucket_name = os.getenv("S3_BUCKET_NAME")
            self._office_directories = os.getenv("S3_CONFIG_FOLDER")

            self._s3_client = boto3.client(
                "s3",
                endpoint_url=os.getenv("S3_BUCKET_ENDPOINT"),
                aws_access_key_id=os.getenv("S3_BUCKET_ACCESS_KEY"),
                aws_secret_access_key=os.getenv("S3_BUCKET_SECRET_KEY"),
                region_name=os.getenv("S3_BUCKET_REGION", "gra"),
            )

            # Test connection by listing bucket (this will raise an exception if credentials are wrong)
            self._s3_client.head_bucket(Bucket=self._bucket_name)

            logger.info(
                f"S3 enabled: Connected to bucket {self._bucket_name}, office_directories: {self._office_directories}"
            )

        except (ClientError, NoCredentialsError) as e:
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
            logger.info(
                f"Downloading configuration file from S3: s3://{self._bucket_name}/{s3_key}"
            )

            response = self._s3_client.get_object(Bucket=self._bucket_name, Key=s3_key)
            file_content = BytesIO(response["Body"].read())

            # Log file size
            file_size = len(file_content.getvalue())
            logger.info(f"Successfully downloaded {s3_key} ({file_size} bytes)")

            return file_content

        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "NoSuchKey":
                raise FileNotFoundError(
                    f"Configuration file not found in S3: {s3_key}"
                ) from e
            else:
                raise Exception(f"Failed to download from S3: {e}") from e
        except Exception as e:
            raise Exception(f"Unexpected error downloading from S3: {e}") from e

    def list_available_config_files(self) -> list[str]:
        """List all available configuration files from S3.

        Returns:
            list[str]: List of configuration file names (without paths).

        Raises:
            Exception: If S3 is not available or listing fails.
        """
        if not self._s3_client or not self._bucket_name or not self._office_directories:
            raise Exception("S3 client, bucket, or office directories not configured")

        try:
            logger.info(
                f"Listing configuration files from S3: {self._office_directories}/"
            )

            # Ensure office_directories ends with / for proper prefix matching
            prefix = self._office_directories
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

            logger.info(f"Found {len(files)} configuration files in S3")
            return sorted(files)

        except ClientError as e:
            error_msg = f"Failed to list configuration files from S3: {e}"
            logger.error(error_msg)
            raise Exception(error_msg) from e
        except Exception as e:
            error_msg = f"Unexpected error listing configuration files: {e}"
            logger.error(error_msg)
            raise Exception(error_msg) from e

    def validate_config_file_exists(self, filename: str) -> bool:
        """Check if a specific configuration file exists in S3.

        Args:
            filename: Name of the configuration file to check.

        Returns:
            bool: True if the file exists, False otherwise.
        """
        if not self._s3_client or not self._bucket_name or not self._office_directories:
            return False

        try:
            # Construct S3 key
            s3_key = f"{self._office_directories}/{filename}"
            if self._office_directories.endswith("/"):
                s3_key = f"{self._office_directories}{filename}"

            # Try to get object metadata
            self._s3_client.head_object(Bucket=self._bucket_name, Key=s3_key)
            logger.info(f"Configuration file exists in S3: {filename}")
            return True

        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                logger.warning(f"Configuration file not found in S3: {filename}")
                return False
            else:
                logger.error(f"Error checking file existence: {e}")
                return False
        except Exception as e:
            logger.error(f"Unexpected error checking file existence: {e}")
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
        if not self._office_directories:
            raise Exception("S3 office directories not configured")

        logger.info(f"Loading configuration file from S3: {filename}")

        # Construct S3 key
        s3_key = f"{self._office_directories}/{filename}"
        if self._office_directories.endswith("/"):
            s3_key = f"{self._office_directories}{filename}"

        try:
            file_content = self._download_from_s3(s3_key)
            excel_data = pd.read_excel(file_content, sheet_name=None)
            logger.info(
                f"Loaded configuration from S3 - filename: {filename}, sheets: {list(excel_data.keys())}"
            )
            return excel_data
        except FileNotFoundError:
            # Re-raise FileNotFoundError as-is
            raise
        except Exception as e:
            error_msg = f"Failed to load configuration file '{filename}' from S3: {e}"
            logger.error(error_msg)
            raise Exception(error_msg) from e


# Global instance
_s3_config_service = None


def get_s3_config_service() -> S3ConfigService:
    """Get the global S3ConfigService instance.

    Returns:
        S3ConfigService: The global service instance.
    """
    global _s3_config_service
    if _s3_config_service is None:
        _s3_config_service = S3ConfigService()
    return _s3_config_service
