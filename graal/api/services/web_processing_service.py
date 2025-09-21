"""
Web processing service for GRAAL pipeline integration.
"""

import asyncio
import json
import logging
import os
import uuid
from pathlib import Path
from typing import Optional

import aiofiles
import pandas as pd

from graal.api.models.responses import (
    AmendmentPreview,
    JobStatus,
    PreviewResponse,
    ProcessingResponse,
    ProgressResponse,
)
from graal.api.services.job_registry import InMemoryJobRegistry, JobRegistry
from graal.core.processing_pipeline import ProcessingPipeline
from graal.full_pipeline import load_config

logger = logging.getLogger(__name__)


class WebProcessingService:
    """Service for web-based processing of amendments."""

    def __init__(self, job_registry: JobRegistry):
        self.config_path = "config/default.yml"
        self.tmp_dir = Path("tmp")
        self.tmp_dir.mkdir(exist_ok=True)
        self.max_file_size = 50 * 1024 * 1024  # 50MB
        self.timeout_seconds = 60 * 60  # 60 minutes
        self.job_registry = job_registry
        self._background_tasks: set[asyncio.Task] = (
            set()
        )  # Track background tasks to prevent garbage collection

    async def start_processing(
        self, file_content: bytes, filename: str
    ) -> ProcessingResponse:
        """
        Start processing a JSON file.

        Args:
            file_content: Raw file content
            filename: Original filename

        Returns:
            ProcessingResponse with job_id
        """
        # Validate file size
        if len(file_content) > self.max_file_size:
            raise ValueError(
                f"File size {len(file_content)} bytes exceeds maximum {self.max_file_size} bytes"
            )

        # Validate JSON content
        try:
            json.loads(file_content.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            raise ValueError(f"Invalid JSON file: {str(e)}") from e

        # Generate job ID and save file
        job_id = str(uuid.uuid4())
        input_file_path = self.tmp_dir / f"{job_id}_input.json"

        async with aiofiles.open(input_file_path, "wb") as f:
            await f.write(file_content)

        # Register job
        self.job_registry.create_job(job_id, str(input_file_path))

        # Start processing in background
        task = asyncio.create_task(self._process_file_async(job_id))
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)

        return ProcessingResponse(
            job_id=job_id, status=JobStatus.queued, message="Processing job started"
        )

    async def _process_file_async(self, job_id: str) -> None:
        """Process file asynchronously."""
        try:
            job_info = self.job_registry.get_job(job_id)
            if not job_info:
                logger.error(f"Job {job_id} not found in registry")
                return

            input_file_path = job_info["input_file_path"]

            # Update status to running
            self.job_registry.update_job(
                job_id,
                status=JobStatus.running,
                percent=10,
                message="Loading configuration and initializing pipeline",
            )

            # Load configuration
            config = load_config(self.config_path)

            # Update the input file path in config to point to our uploaded file
            # TODO: Make these values come from the frontend in the future
            config["input_files"] = [
                {
                    "path": input_file_path,
                    "default_processing_timestamp": {
                        "year": 2024,
                        "month": 1,
                        "day": 1,
                    },
                    "origin_project": "Web Upload",
                }
            ]

            # Set output path
            output_file_path = self.tmp_dir / f"{job_id}_output.csv"
            config["output"]["file_prefix_template"] = str(output_file_path).replace(
                ".csv", ""
            )

            self.job_registry.update_job(
                job_id, percent=20, message="Starting GRAAL pipeline processing"
            )

            # Run pipeline with timeout
            pipeline = ProcessingPipeline()

            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()

            def run_pipeline():
                try:
                    pipeline.run(config)
                    return True
                except Exception as e:
                    logger.error(f"Pipeline execution failed: {str(e)}")
                    raise

            # Execute with timeout
            try:
                await asyncio.wait_for(
                    loop.run_in_executor(None, run_pipeline),
                    timeout=self.timeout_seconds,
                )
            except asyncio.TimeoutError:
                self.job_registry.update_job(
                    job_id,
                    status=JobStatus.timeout,
                    message="Processing timed out after 60 minutes",
                )
                return

            # Find the actual output file (pipeline adds timestamp)
            csv_files = list(self.tmp_dir.glob(f"{job_id}_output_*.csv"))
            if not csv_files:
                raise FileNotFoundError("No CSV output file found")

            actual_output_path = csv_files[0]

            self.job_registry.update_job(
                job_id,
                status=JobStatus.completed,
                percent=100,
                message="Processing completed successfully",
                output_file_path=str(actual_output_path),
            )

        except Exception as e:
            logger.error(f"Error processing job {job_id}: {str(e)}")
            self.job_registry.update_job(
                job_id,
                status=JobStatus.failed,
                message=f"Processing failed: {str(e)}",
                error=str(e),
            )

    def get_job_status(self, job_id: str) -> Optional[ProgressResponse]:
        """Get the current status of a processing job."""
        job_info = self.job_registry.get_job(job_id)
        if not job_info:
            return None

        return ProgressResponse(
            job_id=job_id,
            status=job_info["status"],
            percent=job_info["percent"],
            message=job_info["message"],
            started_at=job_info["started_at"],
            updated_at=job_info["updated_at"],
        )

    def get_results_preview(self, job_id: str) -> Optional[PreviewResponse]:
        """Get a preview of the processing results (first 10 rows)."""
        job_info = self.job_registry.get_job(job_id)
        if not job_info or job_info["status"] != JobStatus.completed:
            return None

        output_file_path = job_info.get("output_file_path")
        if not output_file_path or not os.path.exists(output_file_path):
            return None

        try:
            # Read CSV file
            df = pd.read_csv(output_file_path)

            # Get first 10 rows
            preview_df = df.head(10)

            # Convert to list of AmendmentPreview objects
            preview_rows = []
            for _, row in preview_df.iterrows():
                preview_rows.append(
                    AmendmentPreview(
                        num_amdt=row.get("Num amdt"),
                        commentaires=row.get("Commentaires"),
                        allotissement=row.get("Allotissement"),
                        objet_amdt=row.get("Objet amdt"),
                        sort=row.get("Sort"),
                        reponse=row.get("Réponse"),
                        affectation_email=row.get("Affectation (email)"),
                        affectation_nom=row.get("Affectation (nom)"),
                        entite_pilote=row.get("Entité Pilote"),
                        avis_du_gouvernement=row.get("Avis du Gouvernement"),
                        groupe=row.get("Groupe"),
                        num_article=row.get("Num article"),
                        expose_amdt=row.get("Exposé amdt"),
                        corps_amdt=row.get("Corps amdt"),
                        mission=row.get("Mission"),
                    )
                )

            return PreviewResponse(
                job_id=job_id,
                total_rows=len(df),
                preview_rows=preview_rows,
                columns=list(df.columns),
            )

        except Exception as e:
            logger.error(f"Error reading results for job {job_id}: {str(e)}")
            return None

    def get_results_file_path(self, job_id: str) -> Optional[str]:
        """Get the path to the results CSV file for download."""
        job_info = self.job_registry.get_job(job_id)
        if not job_info or job_info["status"] != JobStatus.completed:
            return None

        return job_info.get("output_file_path")


# Global job registry instance
job_registry = InMemoryJobRegistry()
# Global service instance
web_processing_service = WebProcessingService(job_registry=job_registry)
