"""
Unit tests for DSPy prompt storage module.

Tests cover:
- Saving optimized prompts with versioning
- Loading prompts with caching
- Listing available prompts
- Getting prompt metadata
- Error handling for missing/invalid prompts
- Cache behavior and invalidation
"""

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from graal.summary.dspy_modules.storage import (
    DSPyPromptStorage,
    InvalidPromptDataError,
    PromptNotFoundError,
    PromptStorageError,
    get_dspy_prompt_storage,
)


@pytest.fixture
def sample_prompt_data() -> dict[str, Any]:
    """Create sample prompt data for testing."""
    return {
        "version": "1.0",
        "metadata": {
            "office": "office_A",
            "model": "albert",
            "created_at": "2025-10-23T14:30:00Z",
            "optimizer": "MIPROv2",
            "training_dataset": "s3://path/to/dataset",
            "training_samples": 100,
            "optimization_metrics": {
                "final_score": 0.87,
                "semantic_score": 0.91,
                "length_score": 0.82,
                "verb_form_score": 0.65,
            },
            "hyperparameters": {
                "num_candidates": 10,
                "num_iterations": 5,
            },
        },
        "prompt": {
            "instructions": "Generate a concise summary...",
            "examples": [],
            "signature": "AmendmentSummary",
        },
    }


@pytest.fixture
def mock_aioboto3_session():
    """Create a mock aioboto3 session."""
    mock_session = MagicMock()
    mock_client = AsyncMock()
    mock_session.client.return_value.__aenter__.return_value = mock_client
    return mock_session, mock_client


class TestDSPyPromptStorageInitialization:
    """Test storage initialization and configuration."""

    def test_initialization_success(self):
        """Test successful initialization with valid S3 config."""
        with patch("graal.summary.dspy_modules.storage.aioboto3.Session"):
            storage = DSPyPromptStorage(base_path="summary_prompts/", cache_ttl=300)
            assert storage.base_path == "summary_prompts/"
            assert storage.cache_ttl == 300
            assert storage._bucket_name == "graal-dev-app"

    def test_initialization_missing_env_vars(self, monkeypatch):
        """Test initialization fails with missing environment variables."""
        monkeypatch.delenv("S3_BUCKET_NAME", raising=False)
        with pytest.raises(PromptStorageError, match="Missing environment variables"):
            DSPyPromptStorage()

    def test_base_path_normalization(self):
        """Test that base path is normalized with trailing slash."""
        with patch("graal.summary.dspy_modules.storage.aioboto3.Session"):
            storage = DSPyPromptStorage(base_path="prompts")
            assert storage.base_path == "prompts/"


class TestPromptValidation:
    """Test prompt data validation."""

    def test_validate_valid_prompt(self, sample_prompt_data):
        """Test validation passes for valid prompt data."""
        with patch("graal.summary.dspy_modules.storage.aioboto3.Session"):
            storage = DSPyPromptStorage()
            # Should not raise any exception
            storage._validate_prompt_data(sample_prompt_data)

    def test_validate_missing_version(self, sample_prompt_data):
        """Test validation fails when version field is missing."""
        with patch("graal.summary.dspy_modules.storage.aioboto3.Session"):
            storage = DSPyPromptStorage()
            del sample_prompt_data["version"]
            with pytest.raises(InvalidPromptDataError, match="Missing required fields"):
                storage._validate_prompt_data(sample_prompt_data)

    def test_validate_missing_metadata(self, sample_prompt_data):
        """Test validation fails when metadata is missing."""
        with patch("graal.summary.dspy_modules.storage.aioboto3.Session"):
            storage = DSPyPromptStorage()
            del sample_prompt_data["metadata"]
            with pytest.raises(InvalidPromptDataError, match="Missing required fields"):
                storage._validate_prompt_data(sample_prompt_data)

    def test_validate_missing_metadata_fields(self, sample_prompt_data):
        """Test validation fails when required metadata fields are missing."""
        with patch("graal.summary.dspy_modules.storage.aioboto3.Session"):
            storage = DSPyPromptStorage()
            del sample_prompt_data["metadata"]["office"]
            with pytest.raises(
                InvalidPromptDataError, match="Missing required metadata fields"
            ):
                storage._validate_prompt_data(sample_prompt_data)

    def test_validate_invalid_prompt_structure(self, sample_prompt_data):
        """Test validation fails when prompt is not a dictionary."""
        with patch("graal.summary.dspy_modules.storage.aioboto3.Session"):
            storage = DSPyPromptStorage()
            sample_prompt_data["prompt"] = "not a dict"
            with pytest.raises(InvalidPromptDataError, match="must be a dictionary"):
                storage._validate_prompt_data(sample_prompt_data)


class TestSaveOptimizedPrompt:
    """Test saving optimized prompts."""

    @pytest.mark.asyncio
    async def test_save_prompt_success(self, sample_prompt_data, mock_aioboto3_session):
        """Test successful prompt save creates both versioned and latest files."""
        mock_session, mock_client = mock_aioboto3_session
        mock_client.put_object = AsyncMock()

        with patch(
            "graal.summary.dspy_modules.storage.aioboto3.Session",
            return_value=mock_session,
        ):
            storage = DSPyPromptStorage()
            version = await storage.save_optimized_prompt(
                office="office_A",
                model="albert",
                prompt_data=sample_prompt_data,
            )

            # Verify version format (YYYY-MM-DD_HH-MM-SS)
            assert len(version) == 19
            assert version[4] == "-" and version[7] == "-"
            assert version[10] == "_" and version[13] == "-"

            # Verify two put_object calls (versioned + latest)
            assert mock_client.put_object.call_count == 2

            # Check versioned file
            versioned_call = mock_client.put_object.call_args_list[0]
            assert f"summary_prompts/office_A/albert/{version}.json" in str(
                versioned_call
            )

            # Check latest file
            latest_call = mock_client.put_object.call_args_list[1]
            assert "summary_prompts/office_A/albert/latest.json" in str(latest_call)

    @pytest.mark.asyncio
    async def test_save_prompt_updates_metadata(
        self, sample_prompt_data, mock_aioboto3_session
    ):
        """Test that save updates office and model in metadata."""
        mock_session, mock_client = mock_aioboto3_session
        mock_client.put_object = AsyncMock()

        with patch(
            "graal.summary.dspy_modules.storage.aioboto3.Session",
            return_value=mock_session,
        ):
            storage = DSPyPromptStorage()
            await storage.save_optimized_prompt(
                office="office_B",
                model="scaleway",
                prompt_data=sample_prompt_data,
            )

            # Verify metadata was updated
            assert sample_prompt_data["metadata"]["office"] == "office_B"
            assert sample_prompt_data["metadata"]["model"] == "scaleway"
            assert "created_at" in sample_prompt_data["metadata"]

    @pytest.mark.asyncio
    async def test_save_prompt_invalidates_cache(
        self, sample_prompt_data, mock_aioboto3_session
    ):
        """Test that saving a prompt invalidates relevant cache entries."""
        mock_session, mock_client = mock_aioboto3_session
        mock_client.put_object = AsyncMock()

        with patch(
            "graal.summary.dspy_modules.storage.aioboto3.Session",
            return_value=mock_session,
        ):
            storage = DSPyPromptStorage()

            # Add some cache entries
            storage._cache["office_A_albert_latest"] = ({"data": "test"}, 0.0)
            storage._cache["office_A_albert_v1"] = ({"data": "test"}, 0.0)
            storage._cache["office_B_scaleway_latest"] = ({"data": "test"}, 0.0)

            await storage.save_optimized_prompt(
                office="office_A",
                model="albert",
                prompt_data=sample_prompt_data,
            )

            # Verify only office_A/albert entries were removed
            assert "office_A_albert_latest" not in storage._cache
            assert "office_A_albert_v1" not in storage._cache
            assert "office_B_scaleway_latest" in storage._cache

    @pytest.mark.asyncio
    async def test_save_prompt_invalid_data(self, mock_aioboto3_session):
        """Test that saving invalid prompt data raises error."""
        mock_session, _mock_client = mock_aioboto3_session

        with patch(
            "graal.summary.dspy_modules.storage.aioboto3.Session",
            return_value=mock_session,
        ):
            storage = DSPyPromptStorage()

            invalid_data = {"incomplete": "data"}
            with pytest.raises(InvalidPromptDataError):
                await storage.save_optimized_prompt(
                    office="office_A",
                    model="albert",
                    prompt_data=invalid_data,
                )


class TestLoadOptimizedPrompt:
    """Test loading optimized prompts."""

    @pytest.mark.asyncio
    async def test_load_prompt_success(self, sample_prompt_data, mock_aioboto3_session):
        """Test successful prompt loading."""
        mock_session, mock_client = mock_aioboto3_session

        # Mock S3 response
        prompt_json = json.dumps(sample_prompt_data).encode("utf-8")
        mock_response = {"Body": AsyncMock()}
        mock_response["Body"].read = AsyncMock(return_value=prompt_json)
        mock_client.get_object = AsyncMock(return_value=mock_response)

        with patch(
            "graal.summary.dspy_modules.storage.aioboto3.Session",
            return_value=mock_session,
        ):
            storage = DSPyPromptStorage()
            result = await storage.load_optimized_prompt(
                office="office_A",
                model="albert",
                version="latest",
            )

            assert result == sample_prompt_data
            mock_client.get_object.assert_called_once()

    @pytest.mark.asyncio
    async def test_load_prompt_caching(self, sample_prompt_data, mock_aioboto3_session):
        """Test that loaded prompts are cached."""
        mock_session, mock_client = mock_aioboto3_session

        prompt_json = json.dumps(sample_prompt_data).encode("utf-8")
        mock_response = {"Body": AsyncMock()}
        mock_response["Body"].read = AsyncMock(return_value=prompt_json)
        mock_client.get_object = AsyncMock(return_value=mock_response)

        with patch(
            "graal.summary.dspy_modules.storage.aioboto3.Session",
            return_value=mock_session,
        ):
            storage = DSPyPromptStorage(cache_ttl=300)

            # First load
            result1 = await storage.load_optimized_prompt(
                office="office_A",
                model="albert",
                version="latest",
            )

            # Second load (should use cache)
            result2 = await storage.load_optimized_prompt(
                office="office_A",
                model="albert",
                version="latest",
            )

            assert result1 == result2
            # Should only call S3 once
            assert mock_client.get_object.call_count == 1

    @pytest.mark.asyncio
    async def test_load_prompt_not_found(self, mock_aioboto3_session):
        """Test loading non-existent prompt raises PromptNotFoundError."""
        mock_session, mock_client = mock_aioboto3_session

        # Mock S3 NoSuchKey error
        from botocore.exceptions import ClientError

        error_response = {"Error": {"Code": "NoSuchKey"}}
        mock_client.get_object = AsyncMock(
            side_effect=ClientError(error_response, "GetObject")
        )

        with patch(
            "graal.summary.dspy_modules.storage.aioboto3.Session",
            return_value=mock_session,
        ):
            storage = DSPyPromptStorage()

            with pytest.raises(PromptNotFoundError, match="Prompt not found"):
                await storage.load_optimized_prompt(
                    office="office_A",
                    model="albert",
                    version="nonexistent",
                )

    @pytest.mark.asyncio
    async def test_load_prompt_invalid_json(self, mock_aioboto3_session):
        """Test loading invalid JSON raises InvalidPromptDataError."""
        mock_session, mock_client = mock_aioboto3_session

        # Mock S3 response with invalid JSON
        mock_response = {"Body": AsyncMock()}
        mock_response["Body"].read = AsyncMock(return_value=b"invalid json{")
        mock_client.get_object = AsyncMock(return_value=mock_response)

        with patch(
            "graal.summary.dspy_modules.storage.aioboto3.Session",
            return_value=mock_session,
        ):
            storage = DSPyPromptStorage()

            with pytest.raises(InvalidPromptDataError, match="Invalid JSON"):
                await storage.load_optimized_prompt(
                    office="office_A",
                    model="albert",
                    version="latest",
                )


class TestListAvailablePrompts:
    """Test listing available prompts."""

    @pytest.mark.asyncio
    async def test_list_prompts_for_office(self, mock_aioboto3_session):
        """Test listing all prompts for an office."""
        mock_session, mock_client = mock_aioboto3_session

        # Mock S3 list response
        mock_response = {
            "Contents": [
                {"Key": "summary_prompts/office_A/albert/latest.json"},
                {"Key": "summary_prompts/office_A/albert/2025-10-23_14-30-00.json"},
                {"Key": "summary_prompts/office_A/scaleway/latest.json"},
            ]
        }
        mock_client.list_objects_v2 = AsyncMock(return_value=mock_response)

        with patch(
            "graal.summary.dspy_modules.storage.aioboto3.Session",
            return_value=mock_session,
        ):
            storage = DSPyPromptStorage()
            prompts = await storage.list_available_prompts(office="office_A")

            assert len(prompts) == 3
            # Results are sorted by model then version
            assert prompts[0]["office"] == "office_A"
            assert prompts[0]["model"] == "albert"
            assert prompts[0]["version"] == "2025-10-23_14-30-00"
            assert prompts[1]["version"] == "latest"
            assert prompts[2]["model"] == "scaleway"

    @pytest.mark.asyncio
    async def test_list_prompts_filtered_by_model(self, mock_aioboto3_session):
        """Test listing prompts filtered by model."""
        mock_session, mock_client = mock_aioboto3_session

        mock_response = {
            "Contents": [
                {"Key": "summary_prompts/office_A/albert/latest.json"},
                {"Key": "summary_prompts/office_A/albert/2025-10-23_14-30-00.json"},
            ]
        }
        mock_client.list_objects_v2 = AsyncMock(return_value=mock_response)

        with patch(
            "graal.summary.dspy_modules.storage.aioboto3.Session",
            return_value=mock_session,
        ):
            storage = DSPyPromptStorage()
            prompts = await storage.list_available_prompts(
                office="office_A",
                model="albert",
            )

            assert len(prompts) == 2
            assert all(p["model"] == "albert" for p in prompts)

    @pytest.mark.asyncio
    async def test_list_prompts_empty(self, mock_aioboto3_session):
        """Test listing prompts when none exist."""
        mock_session, mock_client = mock_aioboto3_session

        mock_response: dict[str, list[dict[str, str]]] = {}  # No Contents key
        mock_client.list_objects_v2 = AsyncMock(return_value=mock_response)

        with patch(
            "graal.summary.dspy_modules.storage.aioboto3.Session",
            return_value=mock_session,
        ):
            storage = DSPyPromptStorage()
            prompts = await storage.list_available_prompts(office="office_A")

            assert len(prompts) == 0


class TestGetPromptMetadata:
    """Test getting prompt metadata."""

    @pytest.mark.asyncio
    async def test_get_metadata_success(
        self, sample_prompt_data, mock_aioboto3_session
    ):
        """Test successfully getting prompt metadata."""
        mock_session, mock_client = mock_aioboto3_session

        prompt_json = json.dumps(sample_prompt_data).encode("utf-8")
        mock_response = {"Body": AsyncMock()}
        mock_response["Body"].read = AsyncMock(return_value=prompt_json)
        mock_client.get_object = AsyncMock(return_value=mock_response)

        with patch(
            "graal.summary.dspy_modules.storage.aioboto3.Session",
            return_value=mock_session,
        ):
            storage = DSPyPromptStorage()
            metadata = await storage.get_prompt_metadata(
                office="office_A",
                model="albert",
                version="latest",
            )

            assert metadata == sample_prompt_data["metadata"]
            assert "office" in metadata
            assert "model" in metadata
            assert "created_at" in metadata


class TestCacheManagement:
    """Test cache management functionality."""

    def test_clear_cache(self):
        """Test clearing all cache entries."""
        with patch("graal.summary.dspy_modules.storage.aioboto3.Session"):
            storage = DSPyPromptStorage()

            # Add cache entries
            storage._cache["key1"] = ({"data": "test1"}, 0.0)
            storage._cache["key2"] = ({"data": "test2"}, 0.0)

            storage.clear_cache()

            assert len(storage._cache) == 0

    def test_get_s3_key(self):
        """Test S3 key construction."""
        with patch("graal.summary.dspy_modules.storage.aioboto3.Session"):
            storage = DSPyPromptStorage(base_path="prompts/")

            key = storage._get_s3_key("office_A", "albert", "latest")
            assert key == "prompts/office_A/albert/latest.json"

    def test_get_cache_key(self):
        """Test cache key construction."""
        with patch("graal.summary.dspy_modules.storage.aioboto3.Session"):
            storage = DSPyPromptStorage()

            key = storage._get_cache_key("office_A", "albert", "latest")
            assert key == "office_A_albert_latest"


class TestSingletonPattern:
    """Test singleton instance management."""

    def test_get_dspy_prompt_storage_singleton(self):
        """Test that get_dspy_prompt_storage returns singleton instance."""
        with patch("graal.summary.dspy_modules.storage.aioboto3.Session"):
            # Clear any existing instance
            import graal.summary.dspy_modules.storage as storage_module

            storage_module._storage_instance = None

            storage1 = get_dspy_prompt_storage()
            storage2 = get_dspy_prompt_storage()

            assert storage1 is storage2
