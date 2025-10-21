"""
Service for loading similarity database files from S3.

This service provides caching for similarity databases loaded from S3 as Parquet files.
Only Parquet format is supported for cloud-native storage efficiency.
"""

import logging
from pathlib import Path
from typing import Dict

import pandas as pd

from graal.utils.s3_service import get_s3_service

logger = logging.getLogger(__name__)


class SimilarityDatabaseLoader:
    """Loader for similarity database files with caching support."""

    def __init__(self):
        """Initialize the similarity database loader with empty cache."""
        self._cache: Dict[str, pd.DataFrame] = {}
        self._s3_service = get_s3_service()

    async def load_from_s3(self, s3_path: str) -> pd.DataFrame:
        """Load a similarity database from S3 with caching.

        Args:
            s3_path: Path relative to similarity folder (e.g., "PLFSS/2024.parquet")

        Returns:
            pd.DataFrame: The loaded similarity database.

        Raises:
            FileNotFoundError: If the file is not found in S3.
            Exception: If there's an error loading the file.
        """
        # Check cache first
        if s3_path in self._cache:
            logger.info(f"Loading similarity database from cache: {s3_path}")
            return self._cache[s3_path].copy()

        # Load from S3
        logger.info(f"Loading similarity database from S3: {s3_path}")
        df = await self._s3_service.load_database_parquet(s3_path)

        # Cache the result
        self._cache[s3_path] = df
        logger.info(
            f"Cached similarity database: {s3_path}, shape: {df.shape}, "
            f"total cached: {len(self._cache)}"
        )

        return df.copy()

    def load_from_local(self, file_path: str) -> pd.DataFrame:
        """Load a similarity database from local file system.

        Args:
            file_path: Absolute or relative path to a local Parquet file

        Returns:
            pd.DataFrame: The loaded similarity database.

        Raises:
            FileNotFoundError: If the file is not found locally.
            Exception: If there's an error loading the file.
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Local file not found: {file_path}")

        logger.info(f"Loading similarity database from local file: {file_path}")
        df = pd.read_parquet(path)
        logger.info(f"Loaded local Parquet file, shape: {df.shape}")

        return df

    def clear_cache(self) -> None:
        """Clear the entire cache."""
        cache_size = len(self._cache)
        self._cache.clear()
        logger.info(f"Cleared similarity database cache ({cache_size} entries)")

    def add_to_cache(self, cache_key: str, df: pd.DataFrame) -> None:
        """Add a pre-loaded database to the cache.

        Args:
            cache_key: The key to use for caching (e.g., "test_db" or "PLFSS/2024")
            df: The DataFrame to cache
        """
        self._cache[cache_key] = df.copy()
        logger.info(
            f"Added database to cache: {cache_key}, shape: {df.shape}, "
            f"total cached: {len(self._cache)}"
        )

    def remove_from_cache(self, cache_key: str) -> bool:
        """Remove a specific database from cache.

        Args:
            cache_key: The cache key to remove

        Returns:
            bool: True if the entry was removed, False if it wasn't in cache
        """
        if cache_key in self._cache:
            del self._cache[cache_key]
            logger.info(f"Removed from cache: {cache_key}")
            return True
        return False

    def get_cache_info(self) -> Dict[str, int | list[str]]:
        """Get information about cached databases.

        Returns:
            Dict with cache statistics
        """
        return {
            "cached_databases": len(self._cache),
            "database_paths": list(self._cache.keys()),
        }


# Global instance
_similarity_db_loader: SimilarityDatabaseLoader | None = None


def get_similarity_db_loader() -> SimilarityDatabaseLoader:
    """Get the global SimilarityDatabaseLoader instance.

    Returns:
        SimilarityDatabaseLoader: The global loader instance.
    """
    global _similarity_db_loader
    if _similarity_db_loader is None:
        _similarity_db_loader = SimilarityDatabaseLoader()
    return _similarity_db_loader
