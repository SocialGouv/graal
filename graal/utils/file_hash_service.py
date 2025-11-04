"""
Service for computing file hashes for deduplication.

This service provides SHA256 hashing capabilities for identifying
and deduplicating uploaded files in the input file pool.
"""

import hashlib
import logging
import logging.config
import threading
from pathlib import Path

logging.config.fileConfig("logging.conf")


class FileHashService:
    """Service for computing SHA256 hashes of files for deduplication."""

    @staticmethod
    async def compute_file_hash(file_content: bytes) -> str:
        """Compute SHA256 hash of file content.

        This method runs the CPU-bound hashing operation in a thread pool
        to avoid blocking the async event loop.

        Args:
            file_content: Byte content of the file to hash.

        Returns:
            str: Hexadecimal SHA256 hash of the file content (64 characters).

        Example:
            >>> service = FileHashService()
            >>> content = b"example file content"
            >>> hash_value = await service.compute_file_hash(content)
            >>> len(hash_value)
            64
        """
        try:
            logging.debug(f"Computing hash for {len(file_content)} bytes")

            file_hash = hashlib.sha256(file_content).hexdigest()
            logging.debug(f"Computed hash: {file_hash}")
            return file_hash

        except Exception as e:
            error_msg = f"Failed to compute hash for file content: {e}"
            logging.error(error_msg)
            raise Exception(error_msg) from e

    @staticmethod
    def hash_to_s3_key(file_hash: str, original_filename: str) -> str:
        """Convert file hash to S3 key preserving original file extension.

        Args:
            file_hash: SHA256 hash of the file.
            original_filename: Original filename to extract extension from.

        Returns:
            str: S3 key in format "input_files/pool/{hash}.{ext}".

        Example:
            >>> hash_to_s3_key("abc123", "lecture.json")
            "input_files/pool/abc123.json"
        """
        # Extract file extension (including the dot)
        extension = Path(original_filename).suffix

        # Build S3 key with hash and extension
        s3_key = f"input_files/pool/{file_hash}{extension}"

        logging.debug(f"Generated S3 key: {s3_key} for file: {original_filename}")
        return s3_key


# Global singleton instance
_file_hash_service: FileHashService | None = None
_lock = threading.Lock()


def get_file_hash_service() -> FileHashService:
    """Get the global FileHashService singleton instance.
    Returns:
        FileHashService: The global file hash service instance.
    """
    global _file_hash_service
    if _file_hash_service is None:
        with _lock:
            if _file_hash_service is None:
                _file_hash_service = FileHashService()
                logging.info("Initialized FileHashService singleton")
    return _file_hash_service
