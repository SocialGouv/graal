"""
Tests for the SimilarityDatabaseBuilderService.

This module tests the core functionality of building similarity databases
from amendment files, including initialization, database building, and
exception handling.
"""

import pandas as pd
import pytest
from pathlib import Path
from unittest.mock import AsyncMock

from graal.utils.config.base_config import InputFileConfig
from graal.utils.similarity_db_builder_service import (
    SimilarityDatabaseBuilderService,
    InvalidProjectError,
    EmptyDatasetError,
    SimilarityDBBuildError,
    get_similarity_db_builder,
)


class TestSimilarityDatabaseBuilderService:
    """Test suite for SimilarityDatabaseBuilderService."""

    def test_initialization(self):
        """Test basic initialization of the service."""
        service = SimilarityDatabaseBuilderService(
            office_config_file_path="test_config.xlsx"
        )
        assert service._office_config_file_path == "test_config.xlsx"

    def test_initialization_default_config(self):
        """Test initialization with default config file path."""
        service = SimilarityDatabaseBuilderService()
        assert "Fichier de configuration GRAAL" in service._office_config_file_path

    @pytest.mark.asyncio
    async def test_build_database_empty_dataset_error(self, mocker):
        """Test that EmptyDatasetError is raised when no amendments are available."""
        service = SimilarityDatabaseBuilderService()

        # Mock dependencies
        mock_loader = mocker.MagicMock()
        mock_loader.excel_data = {"Acronymes": pd.DataFrame()}
        mocker.patch(
            "graal.utils.similarity_db_builder_service.SheetDataLoader",
            return_value=mock_loader,
        )
        mocker.patch(
            "graal.utils.similarity_db_builder_service.AmendmentPreProcessor.load_acronyms",
            return_value={},
        )
        # Use AsyncMock since build_database awaits this method
        service._load_and_preprocess_amendments = AsyncMock(return_value=pd.DataFrame())

        amendment_files: dict[Path, InputFileConfig] = {
            Path("test.json"): {
                "default_processing_timestamp": 1234567890,
                "origin_project": "TEST",
            }
        }

        with pytest.raises(EmptyDatasetError, match="No amendments available"):
            await service.build_database(amendment_files)

    @pytest.mark.asyncio
    async def test_build_database_success(self, mocker):
        """Test successful database building with mocked dependencies."""
        service = SimilarityDatabaseBuilderService()

        # Create sample DataFrame
        sample_df = pd.DataFrame(
            {
                "amdt_idx": [0, 1, 2],
                "Corps amdt": ["Body 1", "Body 2", "Body 3"],
                "Exposé amdt": ["Expose 1", "Expose 2", "Expose 3"],
                "Réponse": ["Response 1", "Response 2", "Response 3"],
                "Lecture": ["A 1", "A 1", "A 1"],
                "origin_project": ["TEST", "TEST", "TEST"],
                "Num article": ["1", "1", "1"],
                "timestamp": [1, 2, 3],
            }
        )

        # Mock dependencies
        mock_loader = mocker.MagicMock()
        mock_loader.excel_data = {"Acronymes": pd.DataFrame()}
        mocker.patch(
            "graal.utils.similarity_db_builder_service.SheetDataLoader",
            return_value=mock_loader,
        )
        mocker.patch(
            "graal.utils.similarity_db_builder_service.AmendmentPreProcessor.load_acronyms",
            return_value={},
        )
        # Use AsyncMock since build_database awaits this method
        service._load_and_preprocess_amendments = AsyncMock(return_value=sample_df)
        mocker.patch(
            "graal.utils.similarity_db_builder_service.AllotmentHandler.process_allotments",
            return_value=(sample_df, []),
        )

        amendment_files: dict[Path, InputFileConfig] = {
            Path("test.json"): {
                "default_processing_timestamp": 1234567890,
                "origin_project": "TEST",
            }
        }

        result = await service.build_database(amendment_files)

        assert not result.empty
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_build_database_unexpected_error(self, mocker):
        """Test that unexpected errors are wrapped in SimilarityDBBuildError."""
        service = SimilarityDatabaseBuilderService()

        # Mock to raise an unexpected error
        mocker.patch(
            "graal.utils.similarity_db_builder_service.SheetDataLoader",
            side_effect=RuntimeError("Unexpected error"),
        )

        amendment_files: dict[Path, InputFileConfig] = {
            Path("test.json"): {
                "default_processing_timestamp": 1234567890,
                "origin_project": "TEST",
            }
        }

        with pytest.raises(
            SimilarityDBBuildError, match="Failed to build similarity database"
        ):
            await service.build_database(amendment_files)

    def test_get_all_indices_oldest_or_shorter_responses(self):
        """Test the static method for removing duplicates from clusters."""
        df = pd.DataFrame(
            {
                "amdt_idx": [0, 1, 2, 3],
                "timestamp": [100, 200, 150, 200],
                "Réponse": ["short", "longer response", "medium", "longest response"],
            }
        )

        cluster = [0, 1, 2, 3]

        result = SimilarityDatabaseBuilderService._get_all_indices_oldest_or_shorter_responses(
            df, cluster
        )

        # Should keep the most recent with longest response (index 3)
        # and return all others for removal
        assert 3 not in result
        assert len(result) == 3
        assert set(result) == {0, 1, 2}

    def test_get_all_indices_single_amendment(self):
        """Test removal strategy with a single amendment in cluster."""
        df = pd.DataFrame(
            {
                "amdt_idx": [0],
                "timestamp": [100],
                "Réponse": ["response"],
            }
        )

        cluster = [0]

        result = SimilarityDatabaseBuilderService._get_all_indices_oldest_or_shorter_responses(
            df, cluster
        )

        # Should return empty list (keep the only amendment)
        assert result == []


class TestGetSimilarityDbBuilder:
    """Test suite for the global instance getter."""

    def test_get_similarity_db_builder_creates_instance(self):
        """Test that get_similarity_db_builder creates a new instance."""
        # Reset global instance
        import graal.utils.similarity_db_builder_service as module

        module._similarity_db_builder = None

        builder = get_similarity_db_builder()

        assert isinstance(builder, SimilarityDatabaseBuilderService)

    def test_get_similarity_db_builder_returns_same_instance(self):
        """Test that get_similarity_db_builder returns the same instance."""
        builder1 = get_similarity_db_builder()
        builder2 = get_similarity_db_builder()

        assert builder1 is builder2


class TestCustomExceptions:
    """Test suite for custom exception classes."""

    def test_similarity_db_build_error(self):
        """Test SimilarityDBBuildError can be raised and caught."""
        with pytest.raises(SimilarityDBBuildError, match="Test error"):
            raise SimilarityDBBuildError("Test error")

    def test_invalid_project_error(self):
        """Test InvalidProjectError is a subclass of SimilarityDBBuildError."""
        with pytest.raises(SimilarityDBBuildError):
            raise InvalidProjectError("Invalid project")

    def test_empty_dataset_error(self):
        """Test EmptyDatasetError is a subclass of SimilarityDBBuildError."""
        with pytest.raises(SimilarityDBBuildError):
            raise EmptyDatasetError("Empty dataset")
