"""
Service for managing database manifests.

This service handles creation, loading, updating, and deletion of database manifests,
which track the input files used to build each similarity database.
"""

import json
import logging
import logging.config
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from graal.utils.s3_service import get_s3_service

logging.config.fileConfig("logging.conf")


@dataclass
class InputFileReference:
    """Reference to an input file in the pool.

    Attributes:
        s3_key: Full S3 path to file in pool (e.g., "input_files/pool/abc123.json")
        file_hash: SHA256 hash of file content
        user_provided_filename: Original filename provided by user
        uploaded_at: ISO 8601 timestamp when file was uploaded
        metadata: Additional processing metadata (timestamp, project, etc.)
    """

    s3_key: str
    file_hash: str
    user_provided_filename: str
    uploaded_at: datetime
    metadata: dict[str, Any]


@dataclass
class DatabaseManifest:
    """Database manifest tracking input files and output.

    Attributes:
        database_name: Name of the database
        created_at: ISO 8601 timestamp when database was first created
        last_updated_at: ISO 8601 timestamp when database was last rebuilt
        input_files: List of input files used to build the database
        parquet_output: S3 path to output Parquet file
    """

    database_name: str
    created_at: datetime
    last_updated_at: datetime
    input_files: list[InputFileReference]
    parquet_output: str


class ManifestService:
    """Service for managing database manifests."""

    def __init__(self):
        """Initialize the manifest service."""
        self.s3_service = get_s3_service()
        logging.info("Initialized ManifestService")

    def _serialize_manifest(self, manifest: DatabaseManifest) -> dict[str, Any]:
        """Serialize manifest to JSON-compatible dict.

        Args:
            manifest: DatabaseManifest to serialize.

        Returns:
            dict: JSON-compatible dictionary with ISO 8601 datetime strings.
        """
        manifest_dict = {
            "database_name": manifest.database_name,
            "created_at": manifest.created_at.isoformat(),
            "last_updated_at": manifest.last_updated_at.isoformat(),
            "input_files": [
                {
                    "s3_key": f.s3_key,
                    "file_hash": f.file_hash,
                    "user_provided_filename": f.user_provided_filename,
                    "uploaded_at": f.uploaded_at.isoformat(),
                    "metadata": f.metadata,
                }
                for f in manifest.input_files
            ],
            "parquet_output": manifest.parquet_output,
        }
        return manifest_dict

    def _deserialize_manifest(self, manifest_dict: dict[str, Any]) -> DatabaseManifest:
        """Deserialize manifest from JSON dict.

        Args:
            manifest_dict: JSON dictionary with manifest data.

        Returns:
            DatabaseManifest: Deserialized manifest object.

        Raises:
            ValueError: If manifest structure is invalid.
        """
        try:
            input_files = [
                InputFileReference(
                    s3_key=f["s3_key"],
                    file_hash=f["file_hash"],
                    user_provided_filename=f["user_provided_filename"],
                    uploaded_at=datetime.fromisoformat(f["uploaded_at"]),
                    metadata=f["metadata"],
                )
                for f in manifest_dict["input_files"]
            ]

            manifest = DatabaseManifest(
                database_name=manifest_dict["database_name"],
                created_at=datetime.fromisoformat(manifest_dict["created_at"]),
                last_updated_at=datetime.fromisoformat(
                    manifest_dict["last_updated_at"]
                ),
                input_files=input_files,
                parquet_output=manifest_dict["parquet_output"],
            )
            return manifest

        except (KeyError, ValueError, TypeError) as e:
            error_msg = f"Invalid manifest structure: {e}"
            logging.error(error_msg)
            raise ValueError(error_msg) from e

    def _validate_manifest(self, manifest: DatabaseManifest) -> None:
        """Validate manifest structure and data.

        Args:
            manifest: Manifest to validate.

        Raises:
            ValueError: If manifest is invalid.
        """
        if not manifest.database_name:
            raise ValueError("database_name cannot be empty")

        if not manifest.parquet_output:
            raise ValueError("parquet_output cannot be empty")

        if not manifest.input_files:
            raise ValueError("input_files cannot be empty")

        # Validate each input file reference
        for i, file_ref in enumerate(manifest.input_files):
            if not file_ref.s3_key:
                raise ValueError(f"input_files[{i}].s3_key cannot be empty")
            if not file_ref.file_hash:
                raise ValueError(f"input_files[{i}].file_hash cannot be empty")
            if not file_ref.user_provided_filename:
                raise ValueError(
                    f"input_files[{i}].user_provided_filename cannot be empty"
                )

    def _get_manifest_s3_key(self, database_name: str) -> str:
        """Get S3 key for manifest file.

        Args:
            database_name: Name of the database.

        Returns:
            str: S3 key for manifest file.
        """
        return f"input_files/manifests/{database_name}.json"

    async def create_manifest(
        self,
        database_name: str,
        input_files: list[InputFileReference],
        parquet_output: str,
    ) -> DatabaseManifest:
        """Create a new database manifest.

        Args:
            database_name: Name of the database.
            input_files: List of input file references.
            parquet_output: S3 path to output Parquet file.

        Returns:
            DatabaseManifest: The created manifest.

        Raises:
            ValueError: If manifest data is invalid.
            Exception: If there's an error creating the manifest.
        """
        logging.info(f"Creating manifest for database: {database_name}")

        now = datetime.now(timezone.utc)
        manifest = DatabaseManifest(
            database_name=database_name,
            created_at=now,
            last_updated_at=now,
            input_files=input_files,
            parquet_output=parquet_output,
        )

        # Validate manifest
        self._validate_manifest(manifest)

        try:
            # Serialize and upload to S3
            manifest_dict = self._serialize_manifest(manifest)
            s3_key = self._get_manifest_s3_key(database_name)

            # Upload manifest as JSON
            await self._upload_manifest_to_s3(s3_key, manifest_dict)

            logging.info(
                f"Created manifest for {database_name} with {len(input_files)} files"
            )
            return manifest

        except Exception as e:
            error_msg = f"Failed to create manifest for {database_name}: {e}"
            logging.error(error_msg)
            raise Exception(error_msg) from e

    async def load_manifest(self, database_name: str) -> DatabaseManifest:
        """Load manifest from S3.

        Args:
            database_name: Name of the database.

        Returns:
            DatabaseManifest: The loaded manifest.

        Raises:
            FileNotFoundError: If manifest doesn't exist.
            Exception: If there's an error loading the manifest.
        """
        logging.info(f"Loading manifest for database: {database_name}")

        try:
            s3_key = self._get_manifest_s3_key(database_name)
            manifest_dict = await self._download_manifest_from_s3(s3_key)
            manifest = self._deserialize_manifest(manifest_dict)

            logging.info(
                f"Loaded manifest for {database_name} with {len(manifest.input_files)} files"
            )
            return manifest

        except FileNotFoundError:
            raise
        except Exception as e:
            error_msg = f"Failed to load manifest for {database_name}: {e}"
            logging.error(error_msg)
            raise Exception(error_msg) from e

    async def update_manifest(
        self, database_name: str, additional_files: list[InputFileReference]
    ) -> DatabaseManifest:
        """Update existing manifest with additional files.

        Args:
            database_name: Name of the database.
            additional_files: List of additional file references to add.

        Returns:
            DatabaseManifest: The updated manifest.

        Raises:
            FileNotFoundError: If manifest doesn't exist.
            ValueError: If update data is invalid.
            Exception: If there's an error updating the manifest.
        """
        logging.info(
            f"Updating manifest for {database_name} with {len(additional_files)} new files"
        )

        try:
            # Load existing manifest
            manifest = await self.load_manifest(database_name)

            # Add new files
            manifest.input_files.extend(additional_files)

            # Update timestamp
            manifest.last_updated_at = datetime.now(timezone.utc)

            # Validate updated manifest
            self._validate_manifest(manifest)

            # Save updated manifest
            manifest_dict = self._serialize_manifest(manifest)
            s3_key = self._get_manifest_s3_key(database_name)
            await self._upload_manifest_to_s3(s3_key, manifest_dict)

            logging.info(
                f"Updated manifest for {database_name}, now has {len(manifest.input_files)} total files"
            )
            return manifest

        except FileNotFoundError:
            raise
        except Exception as e:
            error_msg = f"Failed to update manifest for {database_name}: {e}"
            logging.error(error_msg)
            raise Exception(error_msg) from e

    async def delete_manifest(self, database_name: str) -> None:
        """Delete manifest from S3.

        Args:
            database_name: Name of the database.

        Raises:
            Exception: If there's an error deleting the manifest.
        """
        logging.info(f"Deleting manifest for database: {database_name}")

        try:
            s3_key = self._get_manifest_s3_key(database_name)
            await self._delete_manifest_from_s3(s3_key)

            logging.info(f"Deleted manifest for {database_name}")

        except Exception as e:
            error_msg = f"Failed to delete manifest for {database_name}: {e}"
            logging.error(error_msg)
            raise Exception(error_msg) from e

    async def manifest_exists(self, database_name: str) -> bool:
        """Check if manifest exists for database.

        Args:
            database_name: Name of the database.

        Returns:
            bool: True if manifest exists, False otherwise.
        """
        try:
            s3_key = self._get_manifest_s3_key(database_name)
            return await self._manifest_exists_in_s3(s3_key)
        except Exception as e:
            logging.error(f"Error checking manifest existence for {database_name}: {e}")
            return False

    async def _upload_manifest_to_s3(
        self, s3_key: str, manifest_dict: dict[str, Any]
    ) -> None:
        """Upload manifest JSON to S3.

        Args:
            s3_key: S3 key for the manifest file.
            manifest_dict: Manifest data as dictionary.

        Raises:
            Exception: If upload fails.
        """
        try:
            # Get S3 configuration from s3_service
            bucket_name = self.s3_service._bucket_name
            session = self.s3_service._aioboto3_session
            config = self.s3_service._s3_config

            # Convert dict to JSON bytes
            json_bytes = json.dumps(manifest_dict, indent=2).encode("utf-8")

            async with session.client(
                "s3",
                endpoint_url=self.s3_service._s3_client._endpoint.host,
                config=config,
            ) as s3_client:
                await s3_client.put_object(
                    Bucket=bucket_name,
                    Key=s3_key,
                    Body=json_bytes,
                    ContentType="application/json",
                )

            logging.info(f"Uploaded manifest to S3: {s3_key}")

        except Exception as e:
            error_msg = f"Failed to upload manifest to S3 ({s3_key}): {e}"
            logging.error(error_msg)
            raise Exception(error_msg) from e

    async def _download_manifest_from_s3(self, s3_key: str) -> dict[str, Any]:
        """Download and parse manifest JSON from S3.

        Args:
            s3_key: S3 key for the manifest file.

        Returns:
            dict: Parsed manifest data.

        Raises:
            FileNotFoundError: If manifest doesn't exist.
            Exception: If download or parsing fails.
        """
        try:
            from botocore.exceptions import ClientError

            bucket_name = self.s3_service._bucket_name
            session = self.s3_service._aioboto3_session
            config = self.s3_service._s3_config

            async with session.client(
                "s3",
                endpoint_url=self.s3_service._s3_client._endpoint.host,
                config=config,
            ) as s3_client:
                response = await s3_client.get_object(Bucket=bucket_name, Key=s3_key)
                json_bytes = await response["Body"].read()

            # Parse JSON
            manifest_dict = json.loads(json_bytes.decode("utf-8"))
            logging.info(f"Downloaded manifest from S3: {s3_key}")
            return manifest_dict

        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "NoSuchKey":
                raise FileNotFoundError(f"Manifest not found in S3: {s3_key}") from e
            else:
                raise Exception(f"Failed to download manifest from S3: {e}") from e
        except json.JSONDecodeError as e:
            error_msg = f"Failed to parse manifest JSON from {s3_key}: {e}"
            logging.error(error_msg)
            raise Exception(error_msg) from e
        except Exception as e:
            error_msg = f"Unexpected error downloading manifest from S3 ({s3_key}): {e}"
            logging.error(error_msg)
            raise Exception(error_msg) from e

    async def _delete_manifest_from_s3(self, s3_key: str) -> None:
        """Delete manifest from S3.

        Args:
            s3_key: S3 key for the manifest file.

        Raises:
            Exception: If deletion fails.
        """
        try:
            bucket_name = self.s3_service._bucket_name
            session = self.s3_service._aioboto3_session
            config = self.s3_service._s3_config

            async with session.client(
                "s3",
                endpoint_url=self.s3_service._s3_client._endpoint.host,
                config=config,
            ) as s3_client:
                await s3_client.delete_object(Bucket=bucket_name, Key=s3_key)

            logging.info(f"Deleted manifest from S3: {s3_key}")

        except Exception as e:
            error_msg = f"Failed to delete manifest from S3 ({s3_key}): {e}"
            logging.error(error_msg)
            raise Exception(error_msg) from e

    async def _manifest_exists_in_s3(self, s3_key: str) -> bool:
        """Check if manifest exists in S3.

        Args:
            s3_key: S3 key for the manifest file.

        Returns:
            bool: True if manifest exists, False otherwise.
        """
        try:
            from botocore.exceptions import ClientError

            bucket_name = self.s3_service._bucket_name
            session = self.s3_service._aioboto3_session
            config = self.s3_service._s3_config

            async with session.client(
                "s3",
                endpoint_url=self.s3_service._s3_client._endpoint.host,
                config=config,
            ) as s3_client:
                await s3_client.head_object(Bucket=bucket_name, Key=s3_key)

            return True

        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "404":
                return False
            else:
                logging.error(f"Error checking manifest existence: {e}")
                return False
        except Exception as e:
            logging.error(f"Unexpected error checking manifest existence: {e}")
            return False


# Global singleton instance and lock
_manifest_service: ManifestService | None = None
_lock = threading.Lock()


def get_manifest_service() -> ManifestService:
    """Get the global ManifestService singleton instance.

    Returns:
        ManifestService: The global manifest service instance.
    """
    global _manifest_service
    if _manifest_service is None:
        with _lock:
            if _manifest_service is None:
                _manifest_service = ManifestService()
                logging.info("Initialized ManifestService singleton")
    return _manifest_service
