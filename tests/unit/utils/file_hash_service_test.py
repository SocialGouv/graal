"""
Tests for file hashing service.
"""

import pytest

from graal.utils.file_hash_service import FileHashService, get_file_hash_service


class TestFileHashService:
    """Test cases for FileHashService."""

    @pytest.mark.asyncio
    async def test_compute_file_hash(self):
        """Test computing hash from bytes."""
        test_content = b"Test content for hashing"

        service = FileHashService()
        file_hash = await service.compute_file_hash(test_content)

        # Verify hash is computed (SHA256 produces 64-character hex string)
        assert isinstance(file_hash, str)
        assert len(file_hash) == 64
        assert all(c in "0123456789abcdef" for c in file_hash)

        # Verify same content produces same hash
        file_hash2 = await service.compute_file_hash(test_content)
        assert file_hash == file_hash2

    @pytest.mark.asyncio
    async def test_compute_file_hash_large_content(self):
        """Test hashing large content."""
        # Create content larger than typical chunk size
        test_content = b"A" * 10000

        service = FileHashService()
        file_hash = await service.compute_file_hash(test_content)

        # Verify hash is computed correctly
        assert isinstance(file_hash, str)
        assert len(file_hash) == 64

    @pytest.mark.asyncio
    async def test_compute_file_hash_empty_content(self):
        """Test hashing empty content."""
        test_content = b""

        service = FileHashService()
        file_hash = await service.compute_file_hash(test_content)

        # Verify hash is computed (even for empty content)
        assert isinstance(file_hash, str)
        assert len(file_hash) == 64

    def test_hash_to_s3_key_with_extension(self):
        """Test S3 key generation with file extension."""
        service = FileHashService()

        # Test with .json extension
        s3_key = service.hash_to_s3_key("abc123def456", "lecture.json")
        assert s3_key == "input_files/pool/abc123def456.json"

        # Test with .xlsx extension
        s3_key = service.hash_to_s3_key("xyz789", "config.xlsx")
        assert s3_key == "input_files/pool/xyz789.xlsx"

        # Test with .parquet extension
        s3_key = service.hash_to_s3_key("hash123", "database.parquet")
        assert s3_key == "input_files/pool/hash123.parquet"

    def test_hash_to_s3_key_without_extension(self):
        """Test S3 key generation for file without extension."""
        service = FileHashService()

        s3_key = service.hash_to_s3_key("abc123", "noextension")
        assert s3_key == "input_files/pool/abc123"

    def test_hash_to_s3_key_multiple_dots(self):
        """Test S3 key generation for filename with multiple dots."""
        service = FileHashService()

        s3_key = service.hash_to_s3_key("hash456", "file.backup.json")
        assert s3_key == "input_files/pool/hash456.json"

    @pytest.mark.asyncio
    async def test_different_content_produces_different_hashes(self):
        """Test that different content produces different hashes."""
        service = FileHashService()

        content1 = b"Content number one"
        content2 = b"Content number two"

        hash1 = await service.compute_file_hash(content1)
        hash2 = await service.compute_file_hash(content2)

        # Verify different content produces different hashes
        assert hash1 != hash2

    def test_get_file_hash_service_singleton(self):
        """Test that get_file_hash_service returns singleton instance."""
        service1 = get_file_hash_service()
        service2 = get_file_hash_service()

        # Verify same instance is returned
        assert service1 is service2
