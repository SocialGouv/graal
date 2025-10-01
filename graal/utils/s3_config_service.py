"""
Service for loading configuration files from S3 or local filesystem.

This service automatically detects whether S3 configuration is available
and falls back to local files when needed.
"""

import logging
import os
from io import BytesIO
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError

    BOTO3_AVAILABLE = True
except ImportError:
    logger.info("boto3 not available, S3 functionality will be disabled")
    BOTO3_AVAILABLE = False


class S3ConfigService:
    """Service for loading configuration files from S3 or local filesystem."""

    # Mapping of configuration file names to S3 keys
    CONFIG_FILE_MAPPING = {
        "Fichier de configuration GRAAL - DSS - latest.xlsx": "office_directories/Fichier de configuration GRAAL - DSS - latest.xlsx",
        "Fichier de configuration GRAAL - PLF - latest.xlsx": "office_directories/Fichier de configuration GRAAL - PLF - latest.xlsx",
    }

    def __init__(self):
        """Initialize the S3 config service."""
        self._s3_client = None
        self._s3_enabled = self._initialize_s3()

    def _initialize_s3(self) -> bool:
        """Initialize S3 client if configuration is available.

        Returns:
            bool: True if S3 is available and configured, False otherwise.
        """
        if not BOTO3_AVAILABLE:
            logger.info("S3 disabled: boto3 not available")
            return False

        # Check if S3 configuration environment variables are available
        required_vars = [
            "S3_BUCKET_NAME",
            "S3_ENDPOINT",
            "S3_ACCESS_KEY",
            "S3_SECRET_KEY",
        ]
        missing_vars = [var for var in required_vars if not os.getenv(var)]

        if missing_vars:
            logger.info(f"S3 disabled: Missing environment variables: {missing_vars}")
            return False

        # Check if S3 is explicitly disabled
        if os.getenv("USE_S3_CONFIG", "").lower() in ["false", "0", "no"]:
            logger.info("S3 disabled: USE_S3_CONFIG is set to false")
            return False

        try:
            self._s3_client = boto3.client(
                "s3",
                endpoint_url=os.getenv("S3_ENDPOINT"),
                aws_access_key_id=os.getenv("S3_ACCESS_KEY"),
                aws_secret_access_key=os.getenv("S3_SECRET_KEY"),
                region_name=os.getenv("S3_REGION", "gra"),
            )

            # Test connection by listing bucket (this will raise an exception if credentials are wrong)
            bucket_name = os.getenv("S3_BUCKET_NAME")
            self._s3_client.head_bucket(Bucket=bucket_name)

            logger.info(f"S3 enabled: Connected to bucket {bucket_name}")
            return True

        except (ClientError, NoCredentialsError) as e:
            logger.warning(f"S3 disabled: Failed to initialize S3 client: {e}")
            return False
        except Exception as e:
            logger.warning(f"S3 disabled: Unexpected error initializing S3: {e}")
            return False

    def is_s3_enabled(self) -> bool:
        """Check if S3 is enabled and configured.

        Returns:
            bool: True if S3 is available, False otherwise.
        """
        return self._s3_enabled

    def _download_from_s3(self, s3_key: str) -> BytesIO:
        """Download a file from S3 into memory.

        Args:
            s3_key: The S3 key of the file to download.

        Returns:
            BytesIO: The file content as a BytesIO object.

        Raises:
            Exception: If the download fails.
        """
        if not self._s3_enabled:
            raise Exception("S3 is not enabled or configured")

        bucket_name = os.getenv("S3_BUCKET_NAME")

        try:
            logger.info(
                f"Downloading configuration file from S3: s3://{bucket_name}/{s3_key}"
            )

            response = self._s3_client.get_object(Bucket=bucket_name, Key=s3_key)
            file_content = BytesIO(response["Body"].read())

            # Log file size
            file_size = len(file_content.getvalue())
            logger.info(f"Successfully downloaded {s3_key} ({file_size} bytes)")

            return file_content

        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "NoSuchKey":
                raise FileNotFoundError(f"Configuration file not found in S3: {s3_key}")
            else:
                raise Exception(f"Failed to download from S3: {e}")
        except Exception as e:
            raise Exception(f"Unexpected error downloading from S3: {e}")

    def _get_local_path(self, filename: str) -> Path:
        """Get the local path for a configuration file.

        Args:
            filename: The name of the configuration file.

        Returns:
            Path: The local path to the file.
        """
        data_folder = os.getenv("DATA_FOLDER", "data")
        return Path(data_folder) / "config_graal" / filename

    def load_config_excel(self, filename: str) -> dict[str, pd.DataFrame]:
        """Load a configuration Excel file from S3 or local filesystem.

        Args:
            filename: Name of the Excel file or full path (e.g., "Fichier de configuration GRAAL - DSS - latest.xlsx")

        Returns:
            dict[str, pd.DataFrame]: Dictionary mapping sheet names to DataFrames.

        Raises:
            FileNotFoundError: If the file is not found in S3 or locally.
            Exception: If there's an error loading the file.
        """
        logger.info(f"Loading configuration file: {filename}")

        # Extract filename from path if it's a full path
        from pathlib import Path

        actual_filename = Path(filename).name

        # Try S3 first if enabled
        if self._s3_enabled:
            s3_key = self.CONFIG_FILE_MAPPING.get(actual_filename)
            if s3_key:
                try:
                    file_content = self._download_from_s3(s3_key)
                    excel_data = pd.read_excel(file_content, sheet_name=None)
                    logger.info(
                        f"Loaded configuration from S3 - sheets: {list(excel_data.keys())}"
                    )
                    return excel_data
                except Exception as e:
                    logger.warning(
                        f"Failed to load from S3, falling back to local: {e}"
                    )
            else:
                logger.warning(f"No S3 mapping found for file {filename}, trying local")

        # Fallback to local file
        local_path = self._get_local_path(filename)

        if not local_path.exists():
            raise FileNotFoundError(
                f"Configuration file not found locally: {local_path}"
            )

        try:
            logger.info(f"Loading configuration from local file: {local_path}")
            excel_data = pd.read_excel(local_path, sheet_name=None)
            logger.info(
                f"Loaded configuration from local file - sheets: {list(excel_data.keys())}"
            )
            return excel_data
        except Exception as e:
            raise Exception(
                f"Failed to load local configuration file {local_path}: {e}"
            )

    def get_available_files(self) -> list[str]:
        """Get list of available configuration files.

        Returns:
            list[str]: List of available configuration file names.
        """
        available_files = []

        # Check S3 files if enabled
        if self._s3_enabled:
            try:
                bucket_name = os.getenv("S3_BUCKET_NAME")
                response = self._s3_client.list_objects_v2(
                    Bucket=bucket_name, Prefix="office_directories/"
                )

                if "Contents" in response:
                    for obj in response["Contents"]:
                        s3_key = obj["Key"]
                        # Find the filename that maps to this S3 key
                        for filename, mapped_key in self.CONFIG_FILE_MAPPING.items():
                            if mapped_key == s3_key:
                                available_files.append(filename)
                                break

            except Exception as e:
                logger.warning(f"Failed to list S3 files: {e}")

        # Check local files
        data_folder = os.getenv("DATA_FOLDER", "data")
        local_config_dir = Path(data_folder) / "config_graal"

        if local_config_dir.exists():
            for file_path in local_config_dir.glob("*.xlsx"):
                filename = file_path.name
                if filename not in available_files:
                    available_files.append(filename)

        return sorted(available_files)


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
