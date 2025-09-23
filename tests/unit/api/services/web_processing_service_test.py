"""
Tests for WebProcessingService.
"""

import asyncio
import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch

import pandas as pd
import pytest

from graal.api.models.responses import (
    AmendmentPreview,
    JobStatus,
    PreviewResponse,
    ProcessingResponse,
    ProgressResponse,
)
from graal.api.services.job_registry import JobRegistry
from graal.api.services.web_processing_service import WebProcessingService


class TestWebProcessingService:
    """Test WebProcessingService functionality."""

    @pytest.fixture
    def mock_job_registry(self):
        """Mock job registry with common operations."""
        mock_registry = Mock(spec=JobRegistry)
        mock_registry.create_job = Mock()
        mock_registry.update_job = Mock()
        mock_registry.get_job = Mock()
        mock_registry.delete_job = Mock()
        return mock_registry

    @pytest.fixture
    def mock_aiofiles(self):
        """Mock aiofiles operations."""
        with patch("graal.api.services.web_processing_service.aiofiles") as mock_files:
            mock_file = AsyncMock()
            # Configure write to be an async method that returns None
            mock_file.write = AsyncMock(return_value=None)
            mock_context = AsyncMock()
            mock_context.__aenter__ = AsyncMock(return_value=mock_file)
            mock_context.__aexit__ = AsyncMock(return_value=None)
            mock_files.open.return_value = mock_context
            yield mock_files

    @pytest.fixture
    def sample_json_data(self):
        """Sample valid JSON amendment data."""
        return {
            "amendments": [
                {
                    "Num amdt": "1",
                    "Corps amdt": "Test amendment body",
                    "Exposé amdt": "Test amendment expose",
                    "Mission": "Test mission",
                }
            ]
        }

    @pytest.fixture
    def sample_csv_data(self):
        """Sample CSV data for results."""
        return pd.DataFrame(
            {
                "Num amdt": ["1", "2"],
                "Commentaires": ["Comment 1", "Comment 2"],
                "Allotissement": ["Group A", "Group B"],
                "Objet amdt": ["Object 1", "Object 2"],
                "Sort": ["Sort 1", "Sort 2"],
                "Réponse": ["Response 1", "Response 2"],
                "Affectation (email)": ["test1@example.com", "test2@example.com"],
                "Affectation (nom)": ["User 1", "User 2"],
                "Entité Pilote": ["Entity 1", "Entity 2"],
                "Avis du Gouvernement": ["Avis 1", "Avis 2"],
                "Groupe": ["Group 1", "Group 2"],
                "Num article": ["Art 1", "Art 2"],
                "Exposé amdt": ["Expose 1", "Expose 2"],
                "Corps amdt": ["Body 1", "Body 2"],
                "Mission": ["Mission 1", "Mission 2"],
            }
        )

    @pytest.fixture
    def service(self, tmp_path, mock_job_registry):
        """WebProcessingService instance with temporary directory."""
        service = WebProcessingService(job_registry=mock_job_registry)
        service.tmp_dir = tmp_path / "test_tmp"
        service.tmp_dir.mkdir(exist_ok=True)
        return service

    def create_test_file_content(self, data: dict, size_mb: float = 0.001) -> bytes:
        """Create test file content of specified size."""
        json_str = json.dumps(data)
        # Pad with spaces to reach desired size
        target_size = int(size_mb * 1024 * 1024)
        current_size = len(json_str.encode("utf-8"))
        if current_size < target_size:
            padding = " " * (target_size - current_size - 1)
            data["_padding"] = padding
            json_str = json.dumps(data)
        return json_str.encode("utf-8")

    def test_service_initialization(self, mock_job_registry):
        """Test service initialization with default configuration."""
        service = WebProcessingService(job_registry=mock_job_registry)

        assert service.config_path == "config/default.yml"
        assert service.max_file_size == 50 * 1024 * 1024
        assert service.timeout_seconds == 60 * 60
        assert service.job_registry == mock_job_registry
        assert isinstance(service._background_tasks, set)
        assert service.tmp_dir.exists()

    @pytest.mark.asyncio
    async def test_start_processing_valid_json(
        self, service, mock_job_registry, mock_aiofiles, sample_json_data
    ):
        """Test start_processing with valid JSON file."""
        file_content = self.create_test_file_content(sample_json_data)
        filename = "test.json"

        with patch("uuid.uuid4") as mock_uuid:
            mock_uuid.return_value = "test-job-id"

            result = await service.start_processing(file_content, filename)

        # Verify job creation
        mock_job_registry.create_job.assert_called_once_with(
            "test-job-id", str(service.tmp_dir / "test-job-id_input.json")
        )

        # Verify file writing
        mock_aiofiles.open.assert_called_once()
        mock_aiofiles.open.return_value.__aenter__.return_value.write.assert_called_once()

        # Verify response
        assert isinstance(result, ProcessingResponse)
        assert result.job_id == "test-job-id"
        assert result.status == JobStatus.queued
        assert result.message == "Processing job started"

    @pytest.mark.asyncio
    async def test_start_processing_file_too_large(self, service, sample_json_data):
        """Test start_processing with file exceeding size limit."""
        # Create file larger than 50MB
        file_content = self.create_test_file_content(sample_json_data, size_mb=51)
        filename = "large_file.json"

        with pytest.raises(ValueError, match="File size .* exceeds maximum"):
            await service.start_processing(file_content, filename)

    @pytest.mark.asyncio
    async def test_start_processing_invalid_json(self, service):
        """Test start_processing with invalid JSON content."""
        file_content = b"invalid json content"
        filename = "invalid.json"

        with pytest.raises(ValueError, match="Invalid JSON content"):
            await service.start_processing(file_content, filename)

    @pytest.mark.asyncio
    async def test_start_processing_invalid_encoding(self, service):
        """Test start_processing with invalid UTF-8 encoding."""
        file_content = b"\xff\xfe invalid utf-8"
        filename = "invalid_encoding.json"

        with pytest.raises(ValueError, match="Unable to decode file content as UTF-8"):
            await service.start_processing(file_content, filename)

    @pytest.mark.asyncio
    async def test_process_file_async_success(
        self,
        service,
        mock_job_registry,
        tmp_path,
    ):
        """Test successful async file processing."""
        job_id = "test-job-id"
        input_file_path = str(tmp_path / "input.json")
        output_file_path = tmp_path / f"{job_id}_output_20240101_120000.csv"

        # Create mock input file with valid JSON
        input_json_data = {
            "amendements": [
                {
                    "num": "1",
                    "corps": "Test amendment body",
                    "expose": "Test amendment expose",
                    "mission_titre_court": "Test mission",
                    "chambre": "AN",
                    "legislature": "16",
                    "date_derniere_modif": "2024-01-01 12:00:00.000",
                    "article": "1",
                    "groupe": "Test Group",
                    "affectation_email": "",
                    "affectation_name": "",
                    "avis": "",
                    "computed_batch": [],
                    "objet": "",
                    "organe": "",
                    "pilot_entity": "",
                    "reponse": "",
                    "sort": "",
                }
            ]
        }
        # Write the JSON file synchronously to avoid async mock issues
        with open(input_file_path, "w") as f:
            json.dump(input_json_data, f)

        # Create mock output file
        output_file_path.write_text("test,csv,content\n1,2,3")

        # Setup job registry mock
        mock_job_registry.get_job.return_value = {
            "input_file_path": input_file_path,
            "status": JobStatus.queued,
        }

        # Setup service tmp_dir to match test
        service.tmp_dir = tmp_path

        # Mock the dependencies that are needed to prevent real pipeline execution
        with (
            patch(
                "graal.api.services.web_processing_service.load_config"
            ) as mock_load_config,
            patch(
                "graal.api.services.web_processing_service.ProcessingPipeline"
            ) as mock_processing_pipeline,
        ):
            # Setup load_config mock
            mock_load_config.return_value = {
                "input_files": [],
                "output": {"file_prefix_template": "test_output"},
            }

            # Setup processing pipeline mock
            mock_instance = Mock()
            mock_instance.run = Mock()
            mock_processing_pipeline.return_value = mock_instance

            # Run the async processing
            await service._process_file_async(job_id)

        # Verify job updates
        assert mock_job_registry.update_job.call_count >= 3

        # Verify final completion call
        final_call = mock_job_registry.update_job.call_args_list[-1]
        assert final_call[0][0] == job_id  # job_id
        assert final_call[1]["status"] == JobStatus.completed
        assert final_call[1]["percent"] == 100
        assert "completed successfully" in final_call[1]["message"]

    @pytest.mark.asyncio
    async def test_process_file_async_pipeline_failure(
        self, service, mock_job_registry
    ):
        """Test async processing with pipeline failure."""
        job_id = "test-job-id"
        input_file_path = "test_input.json"

        # Setup job registry mock
        mock_job_registry.get_job.return_value = {
            "input_file_path": input_file_path,
            "status": JobStatus.queued,
        }

        # Mock the dependencies and setup pipeline to fail
        with (
            patch(
                "graal.api.services.web_processing_service.load_config"
            ) as mock_load_config,
            patch(
                "graal.api.services.web_processing_service.ProcessingPipeline"
            ) as mock_processing_pipeline,
        ):
            # Setup load_config mock
            mock_load_config.return_value = {
                "input_files": [],
                "output": {"file_prefix_template": "test_output"},
            }

            # Setup pipeline to fail
            mock_processing_pipeline.return_value.run.side_effect = Exception(
                "Pipeline failed"
            )

            # Run the async processing
            await service._process_file_async(job_id)

        # Verify failure handling
        final_call = mock_job_registry.update_job.call_args_list[-1]
        assert final_call[0][0] == job_id
        assert final_call[1]["status"] == JobStatus.failed
        assert "Pipeline failed" in final_call[1]["message"]

    @pytest.mark.asyncio
    async def test_process_file_async_timeout(self, service, mock_job_registry):
        """Test async processing timeout handling."""
        job_id = "test-job-id"
        input_file_path = "test_input.json"

        # Setup job registry mock
        mock_job_registry.get_job.return_value = {
            "input_file_path": input_file_path,
            "status": JobStatus.queued,
        }

        # Temporarily reduce timeout for testing
        original_timeout = service.timeout_seconds
        service.timeout_seconds = 0.1

        try:
            # Mock the dependencies
            with (
                patch(
                    "graal.api.services.web_processing_service.load_config"
                ) as mock_load_config,
                patch(
                    "graal.api.services.web_processing_service.ProcessingPipeline"
                ) as mock_processing_pipeline,
                patch("asyncio.get_event_loop") as mock_loop,
            ):
                # Setup load_config mock
                mock_load_config.return_value = {
                    "input_files": [],
                    "output": {"file_prefix_template": "test_output"},
                }

                # Setup processing pipeline mock
                mock_instance = Mock()
                mock_instance.run = Mock()
                mock_processing_pipeline.return_value = mock_instance

                # Setup timeout
                mock_executor = AsyncMock()
                mock_executor.side_effect = asyncio.TimeoutError()
                mock_loop.return_value.run_in_executor = mock_executor

                await service._process_file_async(job_id)

                # Verify timeout handling
                final_call = mock_job_registry.update_job.call_args_list[-1]
                assert final_call[0][0] == job_id
                assert final_call[1]["status"] == JobStatus.timeout
                assert "timed out" in final_call[1]["message"]
        finally:
            service.timeout_seconds = original_timeout

    @pytest.mark.asyncio
    async def test_process_file_async_job_not_found(self, service, mock_job_registry):
        """Test async processing with non-existent job."""
        job_id = "non-existent-job"
        mock_job_registry.get_job.return_value = None

        # Should handle gracefully without raising exception
        await service._process_file_async(job_id)

        # Should not call update_job since job doesn't exist
        mock_job_registry.update_job.assert_not_called()

    def test_get_job_status_existing_job(self, service, mock_job_registry):
        """Test get_job_status with existing job."""
        job_id = "test-job-id"
        started_at = datetime.now(timezone.utc)
        updated_at = datetime.now(timezone.utc)

        mock_job_registry.get_job.return_value = {
            "status": JobStatus.running,
            "percent": 50,
            "message": "Processing in progress",
            "started_at": started_at,
            "updated_at": updated_at,
        }

        result = service.get_job_status(job_id)

        assert isinstance(result, ProgressResponse)
        assert result.job_id == job_id
        assert result.status == JobStatus.running
        assert result.percent == 50
        assert result.message == "Processing in progress"
        assert result.started_at == started_at
        assert result.updated_at == updated_at

    def test_get_job_status_non_existent_job(self, service, mock_job_registry):
        """Test get_job_status with non-existent job."""
        job_id = "non-existent-job"
        mock_job_registry.get_job.return_value = None

        result = service.get_job_status(job_id)

        assert result is None

    def test_get_results_preview_success(
        self, service, mock_job_registry, sample_csv_data, tmp_path
    ):
        """Test get_results_preview with successful job and valid CSV."""
        job_id = "test-job-id"
        output_file_path = tmp_path / "output.csv"

        # Write sample CSV data - ensure all data is string type
        sample_csv_data.to_csv(output_file_path, index=False)

        mock_job_registry.get_job.return_value = {
            "status": JobStatus.completed,
            "output_file_path": str(output_file_path),
        }

        # Mock pandas.read_csv to return data with string types to avoid Pydantic validation issues
        with patch("pandas.read_csv") as mock_read_csv:
            # Create a DataFrame with all string values
            mock_df = pd.DataFrame(
                {
                    "Num amdt": ["1", "2"],
                    "Commentaires": ["Comment 1", "Comment 2"],
                    "Allotissement": ["Group A", "Group B"],
                    "Objet amdt": ["Object 1", "Object 2"],
                    "Sort": ["Sort 1", "Sort 2"],
                    "Réponse": ["Response 1", "Response 2"],
                    "Affectation (email)": ["test1@example.com", "test2@example.com"],
                    "Affectation (nom)": ["User 1", "User 2"],
                    "Entité Pilote": ["Entity 1", "Entity 2"],
                    "Avis du Gouvernement": ["Avis 1", "Avis 2"],
                    "Groupe": ["Group 1", "Group 2"],
                    "Num article": ["Art 1", "Art 2"],
                    "Exposé amdt": ["Expose 1", "Expose 2"],
                    "Corps amdt": ["Body 1", "Body 2"],
                    "Mission": ["Mission 1", "Mission 2"],
                }
            )
            mock_read_csv.return_value = mock_df

            result = service.get_results_preview(job_id)

        assert isinstance(result, PreviewResponse)
        assert result.job_id == job_id
        assert result.total_rows == 2
        assert len(result.preview_rows) == 2
        assert len(result.columns) == 15

        # Check first preview row
        first_row = result.preview_rows[0]
        assert isinstance(first_row, AmendmentPreview)
        assert first_row.num_amdt == "1"
        assert first_row.commentaires == "Comment 1"
        assert first_row.affectation_email == "test1@example.com"

    def test_get_results_preview_job_not_completed(self, service, mock_job_registry):
        """Test get_results_preview with job not completed."""
        job_id = "test-job-id"
        mock_job_registry.get_job.return_value = {
            "status": JobStatus.running,
        }

        result = service.get_results_preview(job_id)

        assert result is None

    def test_get_results_preview_no_output_file(self, service, mock_job_registry):
        """Test get_results_preview with missing output file."""
        job_id = "test-job-id"
        mock_job_registry.get_job.return_value = {
            "status": JobStatus.completed,
            "output_file_path": "/non/existent/file.csv",
        }

        result = service.get_results_preview(job_id)

        assert result is None

    def test_get_results_preview_csv_read_error(
        self, service, mock_job_registry, tmp_path
    ):
        """Test get_results_preview with CSV read error."""
        job_id = "test-job-id"
        output_file_path = tmp_path / "invalid.csv"

        # Write invalid CSV content
        output_file_path.write_text("invalid,csv\ncontent")

        mock_job_registry.get_job.return_value = {
            "status": JobStatus.completed,
            "output_file_path": str(output_file_path),
        }

        with patch("pandas.read_csv", side_effect=Exception("CSV read error")):
            result = service.get_results_preview(job_id)

        assert result is None

    def test_get_results_file_path_success(self, service, mock_job_registry):
        """Test get_results_file_path with completed job."""
        job_id = "test-job-id"
        output_path = "/path/to/output.csv"

        mock_job_registry.get_job.return_value = {
            "status": JobStatus.completed,
            "output_file_path": output_path,
        }

        result = service.get_results_file_path(job_id)

        assert result == output_path

    def test_get_results_file_path_job_not_completed(self, service, mock_job_registry):
        """Test get_results_file_path with job not completed."""
        job_id = "test-job-id"
        mock_job_registry.get_job.return_value = {
            "status": JobStatus.running,
        }

        result = service.get_results_file_path(job_id)

        assert result is None

    def test_get_results_file_path_non_existent_job(self, service, mock_job_registry):
        """Test get_results_file_path with non-existent job."""
        job_id = "non-existent-job"
        mock_job_registry.get_job.return_value = None

        result = service.get_results_file_path(job_id)

        assert result is None

    def test_get_results_preview_large_dataset(
        self, service, mock_job_registry, tmp_path
    ):
        """Test get_results_preview limits to first 10 rows."""
        job_id = "test-job-id"
        output_file_path = tmp_path / "large_output.csv"

        # Create DataFrame with 20 rows
        large_df = pd.DataFrame(
            {
                "Num amdt": [str(i) for i in range(20)],
                "Commentaires": [f"Comment {i}" for i in range(20)],
                "Corps amdt": [f"Body {i}" for i in range(20)],
            }
        )
        large_df.to_csv(output_file_path, index=False)

        mock_job_registry.get_job.return_value = {
            "status": JobStatus.completed,
            "output_file_path": str(output_file_path),
        }

        # Mock pandas.read_csv to return data with string types
        with patch("pandas.read_csv") as mock_read_csv:
            # Create a DataFrame with all string values (20 rows)
            mock_df = pd.DataFrame(
                {
                    "Num amdt": [str(i) for i in range(20)],
                    "Commentaires": [f"Comment {i}" for i in range(20)],
                    "Corps amdt": [f"Body {i}" for i in range(20)],
                }
            )
            mock_read_csv.return_value = mock_df

            result = service.get_results_preview(job_id)

        assert result is not None
        assert result.total_rows == 20
        assert len(result.preview_rows) == 10  # Limited to first 10
        assert result.preview_rows[0].num_amdt == "0"
        assert result.preview_rows[9].num_amdt == "9"
