"""
S3 storage for optimized DSPy prompts.

This module provides functionality to save, load, and manage optimized DSPy prompts
in S3 with versioning, caching, and metadata support.
"""

import asyncio
import json
import logging
import logging.config
import os
from datetime import datetime, timezone
from typing import Any, Optional

import aioboto3
from botocore.config import Config
from botocore.exceptions import ClientError

logging.config.fileConfig("logging.conf")


class PromptNotFoundError(Exception):
    """Raised when a requested prompt doesn't exist in S3."""

    pass


class PromptStorageError(Exception):
    """Raised when S3 operations fail during prompt storage/retrieval."""

    pass


class InvalidPromptDataError(Exception):
    """Raised when prompt data is malformed or invalid."""

    pass


class DSPyPromptStorage:
    """Service for managing DSPy optimized prompts in S3.

    Provides versioned storage of optimized prompts with automatic
    "latest" version tracking and in-memory caching for performance.

    S3 Path Structure:
        s3://{base_path}/
        ├── office_A/
        │   ├── albert/
        │   │   ├── latest.json
        │   │   └── 2025-10-23_14-30-00.json
        │   └── scaleway/
        │       └── latest.json
        └── office_B/
            └── vllm/
                └── latest.json
    """

    def __init__(self, base_path: str = "summary_prompts/", cache_ttl: int = 300):
        """Initialize the DSPy prompt storage service.

        Args:
            base_path: S3 path prefix for storing prompts (default: "summary_prompts/")
            cache_ttl: Cache time-to-live in seconds (default: 300 = 5 minutes)

        Raises:
            PromptStorageError: If S3 is not properly configured
        """
        self.base_path = base_path.rstrip("/") + "/"
        self.cache_ttl = cache_ttl
        self._aioboto3_session: Any = None
        self._s3_config: Config | None = None
        self._bucket_name: str | None = None
        self._cache: dict[str, tuple[dict[str, Any], float]] = {}
        self._initialize_s3()

    def _initialize_s3(self) -> None:
        """Initialize S3 client with required configuration.

        Raises:
            PromptStorageError: If S3 is not available or not properly configured
        """
        required_vars = [
            "S3_BUCKET_NAME",
            "S3_BUCKET_ENDPOINT",
            "S3_BUCKET_ACCESS_KEY",
            "S3_BUCKET_SECRET_KEY",
        ]
        missing_vars = [var for var in required_vars if not os.getenv(var)]

        if missing_vars:
            raise PromptStorageError(
                f"S3 not configured: Missing environment variables: {missing_vars}"
            )

        try:
            self._bucket_name = os.getenv("S3_BUCKET_NAME")

            # Configure timeouts and retries
            self._s3_config = Config(
                connect_timeout=int(os.getenv("S3_CONNECT_TIMEOUT", "10")),
                read_timeout=int(os.getenv("S3_READ_TIMEOUT", "60")),
                retries={
                    "max_attempts": int(os.getenv("S3_MAX_RETRIES", "3")),
                    "mode": "standard",
                },
            )

            # Initialize aioboto3 session for async operations
            self._aioboto3_session = aioboto3.Session(
                aws_access_key_id=os.getenv("S3_BUCKET_ACCESS_KEY"),
                aws_secret_access_key=os.getenv("S3_BUCKET_SECRET_KEY"),
                region_name=os.getenv("S3_BUCKET_REGION", "gra"),
            )

            logging.info(
                f"DSPy prompt storage initialized: bucket={self._bucket_name}, "
                f"base_path={self.base_path}, cache_ttl={self.cache_ttl}s"
            )

        except Exception as e:
            raise PromptStorageError(f"Failed to initialize S3 client: {e}") from e

    def _get_s3_key(self, office: str, model: str, version: str) -> str:
        """Construct S3 key for a prompt.

        Args:
            office: Office/team name
            model: Model name (albert, scaleway, ollama, vllm)
            version: Version identifier ("latest" or timestamp)

        Returns:
            Full S3 key path
        """
        return f"{self.base_path}{office}/{model}/{version}.json"

    def _get_cache_key(self, office: str, model: str, version: str) -> str:
        """Generate cache key for a prompt.

        Args:
            office: Office/team name
            model: Model name
            version: Version identifier

        Returns:
            Cache key string
        """
        return f"{office}_{model}_{version}"

    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached entry is still valid based on TTL.

        Args:
            cache_key: Cache key to check

        Returns:
            True if cache entry exists and is not expired
        """
        if cache_key not in self._cache:
            return False

        _, cached_time = self._cache[cache_key]
        age = asyncio.get_event_loop().time() - cached_time
        return age < self.cache_ttl

    def _set_cache(self, cache_key: str, data: dict[str, Any]) -> None:
        """Store data in cache with current timestamp.

        Args:
            cache_key: Key for cache entry
            data: Prompt data to cache
        """
        current_time = asyncio.get_event_loop().time()
        self._cache[cache_key] = (data, current_time)
        logging.debug(f"Cached prompt: {cache_key}")

    def _invalidate_cache(self, office: str, model: str) -> None:
        """Invalidate all cache entries for a specific office/model.

        Args:
            office: Office name
            model: Model name
        """
        keys_to_remove = [
            key for key in self._cache if key.startswith(f"{office}_{model}_")
        ]
        for key in keys_to_remove:
            del self._cache[key]
            logging.debug(f"Invalidated cache: {key}")

    def clear_cache(self) -> None:
        """Clear all cached prompts."""
        self._cache.clear()
        logging.info("Cleared all prompt cache")

    def _validate_prompt_data(self, data: dict[str, Any]) -> None:
        """Validate prompt data structure.

        Args:
            data: Prompt data dictionary to validate

        Raises:
            InvalidPromptDataError: If data structure is invalid
        """
        required_fields = ["version", "metadata", "prompt"]
        missing = [f for f in required_fields if f not in data]
        if missing:
            raise InvalidPromptDataError(f"Missing required fields: {missing}")

        # Validate metadata
        required_meta = ["office", "model", "created_at"]
        missing_meta = [f for f in required_meta if f not in data["metadata"]]
        if missing_meta:
            raise InvalidPromptDataError(
                f"Missing required metadata fields: {missing_meta}"
            )

        # Validate prompt structure
        if not isinstance(data["prompt"], dict):
            raise InvalidPromptDataError("Prompt must be a dictionary")

    async def save_optimized_prompt(
        self, office: str, model: str, prompt_data: dict[str, Any]
    ) -> str:
        """Save an optimized prompt to S3 with versioning.

        Creates two versions:
        - A timestamped version (YYYY-MM-DD_HH-MM-SS.json)
        - A "latest" version (latest.json)

        Args:
            office: Office/team name
            model: Model name (albert, scaleway, ollama, vllm)
            prompt_data: Complete prompt data including metadata and prompt

        Returns:
            Timestamp version string (e.g., "2025-10-23_14-30-00")

        Raises:
            InvalidPromptDataError: If prompt data is malformed
            PromptStorageError: If S3 upload fails
        """
        if not self._aioboto3_session or not self._bucket_name:
            raise PromptStorageError("S3 session or bucket not configured")

        # Validate prompt data
        self._validate_prompt_data(prompt_data)

        # Ensure metadata has correct office/model
        prompt_data["metadata"]["office"] = office
        prompt_data["metadata"]["model"] = model

        # Generate timestamp version
        timestamp = datetime.now(timezone.utc)
        version = timestamp.strftime("%Y-%m-%d_%H-%M-%S")
        prompt_data["metadata"]["created_at"] = timestamp.isoformat()

        # Convert to JSON
        try:
            prompt_json = json.dumps(prompt_data, indent=2, ensure_ascii=False)
            prompt_bytes = prompt_json.encode("utf-8")
        except (TypeError, ValueError) as e:
            raise InvalidPromptDataError(f"Failed to serialize prompt data: {e}") from e

        try:
            async with self._aioboto3_session.client(
                "s3",
                endpoint_url=os.getenv("S3_BUCKET_ENDPOINT"),
                config=self._s3_config,
            ) as s3_client:
                # Save timestamped version
                versioned_key = self._get_s3_key(office, model, version)
                await s3_client.put_object(
                    Bucket=self._bucket_name,
                    Key=versioned_key,
                    Body=prompt_bytes,
                    ContentType="application/json",
                )
                logging.info(
                    f"Saved versioned prompt: s3://{self._bucket_name}/{versioned_key}"
                )

                # Save latest version
                latest_key = self._get_s3_key(office, model, "latest")
                await s3_client.put_object(
                    Bucket=self._bucket_name,
                    Key=latest_key,
                    Body=prompt_bytes,
                    ContentType="application/json",
                )
                logging.info(
                    f"Updated latest prompt: s3://{self._bucket_name}/{latest_key}"
                )

            # Invalidate cache for this office/model
            self._invalidate_cache(office, model)

            return version

        except ClientError as e:
            raise PromptStorageError(f"Failed to save prompt to S3: {e}") from e
        except Exception as e:
            raise PromptStorageError(f"Unexpected error saving prompt: {e}") from e

    async def load_optimized_prompt(
        self, office: str, model: str, version: str = "latest"
    ) -> dict[str, Any]:
        """Load an optimized prompt from S3 with caching.

        Args:
            office: Office/team name
            model: Model name (albert, scaleway, ollama, vllm)
            version: Version to load ("latest" or specific timestamp)

        Returns:
            Prompt data dictionary

        Raises:
            PromptNotFoundError: If prompt doesn't exist
            PromptStorageError: If S3 download fails
            InvalidPromptDataError: If loaded data is malformed
        """
        if not self._aioboto3_session or not self._bucket_name:
            raise PromptStorageError("S3 session or bucket not configured")

        # Check cache first
        cache_key = self._get_cache_key(office, model, version)
        if self._is_cache_valid(cache_key):
            logging.debug(f"Retrieved prompt from cache: {cache_key}")
            return self._cache[cache_key][0]

        s3_key = self._get_s3_key(office, model, version)

        try:
            async with self._aioboto3_session.client(
                "s3",
                endpoint_url=os.getenv("S3_BUCKET_ENDPOINT"),
                config=self._s3_config,
            ) as s3_client:
                response = await s3_client.get_object(
                    Bucket=self._bucket_name, Key=s3_key
                )

                # Read and decode JSON
                file_bytes = await response["Body"].read()
                prompt_json = file_bytes.decode("utf-8")
                prompt_data = json.loads(prompt_json)

                logging.info(
                    f"Loaded prompt: s3://{self._bucket_name}/{s3_key} "
                    f"({len(file_bytes)} bytes)"
                )

                # Validate loaded data
                self._validate_prompt_data(prompt_data)

                # Cache the result
                self._set_cache(cache_key, prompt_data)

                return prompt_data

        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "NoSuchKey":
                raise PromptNotFoundError(
                    f"Prompt not found: office={office}, model={model}, version={version}"
                ) from e
            else:
                raise PromptStorageError(f"Failed to load prompt from S3: {e}") from e
        except json.JSONDecodeError as e:
            raise InvalidPromptDataError(f"Invalid JSON in prompt file: {e}") from e
        except Exception as e:
            raise PromptStorageError(f"Unexpected error loading prompt: {e}") from e

    async def list_available_prompts(
        self, office: str, model: Optional[str] = None
    ) -> list[dict[str, str]]:
        """List all available prompts for an office, optionally filtered by model.

        Args:
            office: Office/team name
            model: Optional model name to filter by

        Returns:
            List of dictionaries with keys: office, model, version

        Raises:
            PromptStorageError: If S3 listing fails
        """
        if not self._aioboto3_session or not self._bucket_name:
            raise PromptStorageError("S3 session or bucket not configured")

        # Construct prefix
        if model:
            prefix = f"{self.base_path}{office}/{model}/"
        else:
            prefix = f"{self.base_path}{office}/"

        try:
            async with self._aioboto3_session.client(
                "s3",
                endpoint_url=os.getenv("S3_BUCKET_ENDPOINT"),
                config=self._s3_config,
            ) as s3_client:
                response = await s3_client.list_objects_v2(
                    Bucket=self._bucket_name, Prefix=prefix
                )

                prompts = []
                if "Contents" in response:
                    for obj in response["Contents"]:
                        s3_key = obj["Key"]
                        # Parse key: base_path/office/model/version.json
                        parts = s3_key[len(self.base_path) :].split("/")
                        if len(parts) == 3 and parts[2].endswith(".json"):
                            prompt_office = parts[0]
                            prompt_model = parts[1]
                            version = parts[2][:-5]  # Remove .json

                            prompts.append(
                                {
                                    "office": prompt_office,
                                    "model": prompt_model,
                                    "version": version,
                                }
                            )

                logging.info(
                    f"Listed {len(prompts)} prompts for office={office}, model={model}"
                )
                return sorted(prompts, key=lambda x: (x["model"], x["version"]))

        except ClientError as e:
            raise PromptStorageError(f"Failed to list prompts from S3: {e}") from e
        except Exception as e:
            raise PromptStorageError(f"Unexpected error listing prompts: {e}") from e

    async def get_prompt_metadata(
        self, office: str, model: str, version: str
    ) -> dict[str, Any]:
        """Get metadata for a prompt without loading the full prompt.

        Args:
            office: Office/team name
            model: Model name
            version: Version identifier

        Returns:
            Metadata dictionary

        Raises:
            PromptNotFoundError: If prompt doesn't exist
            PromptStorageError: If S3 operation fails
        """
        # Load full prompt (cached if available)
        prompt_data = await self.load_optimized_prompt(office, model, version)
        return prompt_data["metadata"]


# Singleton instance management
_storage_instance: Optional[DSPyPromptStorage] = None


def get_dspy_prompt_storage(
    base_path: str = "summary_prompts/", cache_ttl: int = 300
) -> DSPyPromptStorage:
    """Get or create the singleton DSPy prompt storage instance.

    Args:
        base_path: S3 path prefix for storing prompts (default: "summary_prompts/")
        cache_ttl: Cache time-to-live in seconds (default: 300)

    Returns:
        DSPyPromptStorage instance

    Raises:
        PromptStorageError: If S3 is not properly configured
    """
    global _storage_instance
    if _storage_instance is None:
        _storage_instance = DSPyPromptStorage(base_path, cache_ttl)
    return _storage_instance
