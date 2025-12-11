import logging
import os
import threading
from typing import Optional

from botocore.config import Config

from graal.utils.s3.config_s3_service import ConfigS3Service
from graal.utils.s3.database_s3_service import DatabaseS3Service
from graal.utils.s3.input_pool_s3_service import InputPoolS3Service


class S3Service:
    """
    Orchestrator for all S3 operations.

    Responsibilities:
    - Load and validate S3 environment variables
    - Create ConfigS3Service, DatabaseS3Service, and InputPoolS3Service
    - Provide a unified API via:
        - s3.config
        - s3.database
        - s3.pool
    """

    def __init__(self):
        self.bucket_name: str = os.getenv("S3_BUCKET_NAME")
        if self.bucket_name is None:
            raise ValueError("S3_BUCKET_NAME environment variable is required")
        self.endpoint_url: str = os.getenv("S3_BUCKET_ENDPOINT")
        if self.endpoint_url is None:
            raise ValueError("S3_BUCKET_ENDPOINT environment variable is required")
        self.access_key: str = os.getenv("S3_BUCKET_ACCESS_KEY")
        if self.access_key is None:
            raise ValueError("S3_ACCESS_KEY environment variable is required")
        self.secret_key: str = os.getenv("S3_BUCKET_SECRET_KEY")
        if self.secret_key is None:
            raise ValueError("S3_SECRET_KEY environment variable is required")
        self.region: str = os.getenv("S3_BUCKET_REGION", "gra")
        if self.region is None:
            raise ValueError("S3_BUCKET_REGION environment variable is required")
        self.config_folder: str = os.getenv("S3_CONFIG_FOLDER")
        if self.config_folder is None:
            raise ValueError("S3_CONFIG_FOLDER environment variable is required")
        self.similarity_db_folder: str = os.getenv("S3_SIMILARITY_DB_FOLDER")
        if self.similarity_db_folder is None:
            raise ValueError("S3_SIMILARITY_DB_FOLDER environment variable is required")
        self.input_pool_folder: str = os.getenv("S3_INPUT_POOL_FOLDER")
        if self.input_pool_folder is None:
            raise ValueError("S3_INPUT_POOL_FOLDER environment variable is required")

        logging.info(
            f"[S3Service] Using bucket={self.bucket_name}, endpoint={self.endpoint_url}"
        )
        self._build_config()

        logging.info("[S3Service] Initializing S3 sub-services...")

        self.config = ConfigS3Service(
            bucket_name=self.bucket_name,
            endpoint_url=self.endpoint_url,
            config_folder=self.config_folder,
            s3_config=self.s3_config,
        )

        self.database = DatabaseS3Service(
            bucket_name=self.bucket_name,
            endpoint_url=self.endpoint_url,
            similarity_db_folder=self.similarity_db_folder,
            s3_config=self.s3_config,
            region_name=self.region,
            access_key=self.access_key,
            secret_key=self.secret_key,
        )

        self.pool = InputPoolS3Service(
            bucket_name=self.bucket_name,
            endpoint_url=self.endpoint_url,
            input_pool_folder=self.input_pool_folder,
            s3_config=self.s3_config,
            region_name=self.region,
            access_key=self.access_key,
            secret_key=self.secret_key,
        )

        logging.info("[S3Service] All S3 sub-services initialized successfully.")

    # -------------------------------------------------------------------------
    # Build shared boto3 Config
    # -------------------------------------------------------------------------
    def _build_config(self):
        self.s3_config = Config(
            connect_timeout=int(os.getenv("S3_CONNECT_TIMEOUT", "10")),
            read_timeout=int(os.getenv("S3_READ_TIMEOUT", "60")),
            retries={
                "max_attempts": int(os.getenv("S3_MAX_RETRIES", "3")),
                "mode": "standard",
            },
        )


# -------------------------------------------------------------------------
# Singleton
# -------------------------------------------------------------------------
_s3_service_instance: Optional[S3Service] = None
_lock = threading.Lock()


def get_s3_service() -> S3Service:
    global _s3_service_instance
    if _s3_service_instance is None:
        with _lock:
            if _s3_service_instance is None:
                _s3_service_instance = S3Service()
                logging.info("[S3Service] Singleton instance created")
    return _s3_service_instance
