"""
Web processing service for GRAAL pipeline integration.
"""

import asyncio
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
from graal.utils.json_utils import load_json

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
        logger.info(
            f"[WEB_SERVICE] Starting processing for file: {filename}, size: {len(file_content)} bytes"
        )

        # Validate file size
        if len(file_content) > self.max_file_size:
            logger.error(
                f"[WEB_SERVICE] File size validation failed - filename: {filename}, size: {len(file_content)} bytes, max: {self.max_file_size} bytes"
            )
            raise ValueError(
                f"File size {len(file_content)} bytes exceeds maximum {self.max_file_size} bytes"
            )

        # Validate JSON content
        try:
            logger.debug(f"[WEB_SERVICE] Validating JSON content for file: {filename}")
            json_data = load_json(file_content, filename)
            logger.info(
                f"[WEB_SERVICE] JSON validation successful - filename: {filename}, records: {len(json_data) if isinstance(json_data, list) else 'N/A'}"
            )
        except ValueError as e:
            logger.error(
                f"[WEB_SERVICE] JSON validation failed - filename: {filename}, error: {str(e)}"
            )
            raise

        # Generate job ID and save file
        job_id = str(uuid.uuid4())
        input_file_path = self.tmp_dir / f"{job_id}_input.json"
        logger.info(
            f"[WEB_SERVICE] Generated job_id: {job_id}, input_file_path: {input_file_path}"
        )

        try:
            async with aiofiles.open(input_file_path, "wb") as f:
                await f.write(file_content)
            logger.debug(
                f"[WEB_SERVICE] File saved successfully - job_id: {job_id}, path: {input_file_path}"
            )
        except Exception as e:
            logger.error(
                f"[WEB_SERVICE] Failed to save input file - job_id: {job_id}, error: {str(e)}"
            )
            raise

        # Register job
        logger.debug(f"[WEB_SERVICE] Registering job in registry - job_id: {job_id}")
        self.job_registry.create_job(job_id, str(input_file_path))

        # Start processing in background
        logger.info(
            f"[WEB_SERVICE] Starting background processing task - job_id: {job_id}"
        )
        task = asyncio.create_task(self._process_file_async(job_id))
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)

        logger.info(
            f"[WEB_SERVICE] Processing job created and queued - job_id: {job_id}, filename: {filename}"
        )
        return ProcessingResponse(
            job_id=job_id, status=JobStatus.queued, message="Processing job started"
        )

    async def _process_file_async(self, job_id: str) -> None:
        """Process file asynchronously."""
        import time

        start_time = time.time()
        logger.info(f"[WEB_SERVICE] Starting async processing for job_id: {job_id}")

        try:
            job_info = self.job_registry.get_job(job_id)
            if not job_info:
                logger.error(
                    f"[WEB_SERVICE] Job not found in registry - job_id: {job_id}"
                )
                return

            input_file_path = job_info["input_file_path"]
            logger.info(
                f"[WEB_SERVICE] Retrieved job info - job_id: {job_id}, input_file: {input_file_path}"
            )

            # Update status to running
            logger.debug(
                f"[WEB_SERVICE] Updating job status to running - job_id: {job_id}"
            )
            self.job_registry.update_job(
                job_id,
                status=JobStatus.running,
                percent=10,
                message="Loading configuration and initializing pipeline",
            )

            # Load configuration
            logger.info(f"[WEB_SERVICE] Loading configuration from: {self.config_path}")
            config = load_config(self.config_path)
            logger.debug(
                f"[WEB_SERVICE] Configuration loaded successfully - job_id: {job_id}"
            )

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
            logger.debug(
                f"[WEB_SERVICE] Updated config with input file - job_id: {job_id}, path: {input_file_path}"
            )

            # Set output path
            output_file_path = self.tmp_dir / f"{job_id}_output.csv"
            config["output"]["file_prefix_template"] = str(output_file_path).replace(
                ".csv", ""
            )
            logger.debug(
                f"[WEB_SERVICE] Set output path template - job_id: {job_id}, template: {config['output']['file_prefix_template']}"
            )

            logger.info(
                f"[WEB_SERVICE] Starting GRAAL pipeline processing - job_id: {job_id}"
            )
            self.job_registry.update_job(
                job_id, percent=20, message="Starting GRAAL pipeline processing"
            )

            # Run pipeline with timeout
            pipeline = ProcessingPipeline()
            logger.debug(
                f"[WEB_SERVICE] Created ProcessingPipeline instance - job_id: {job_id}"
            )

            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()

            def run_pipeline():
                try:
                    logger.info(
                        f"[WEB_SERVICE] Executing pipeline.run() - job_id: {job_id}"
                    )
                    pipeline.run(config)
                    logger.info(
                        f"[WEB_SERVICE] Pipeline execution completed successfully - job_id: {job_id}"
                    )
                    return True
                except Exception as e:
                    logger.error(
                        f"[WEB_SERVICE] Pipeline execution failed - job_id: {job_id}, error: {str(e)}",
                        exc_info=True,
                    )
                    raise

            # Execute with timeout
            try:
                logger.debug(
                    f"[WEB_SERVICE] Starting pipeline execution with timeout: {self.timeout_seconds}s - job_id: {job_id}"
                )
                await asyncio.wait_for(
                    loop.run_in_executor(None, run_pipeline),
                    timeout=self.timeout_seconds,
                )
                pipeline_time = time.time() - start_time
                logger.info(
                    f"[WEB_SERVICE] Pipeline execution completed in {pipeline_time:.2f}s - job_id: {job_id}"
                )
            except asyncio.TimeoutError:
                logger.error(
                    f"[WEB_SERVICE] Pipeline execution timed out after {self.timeout_seconds}s - job_id: {job_id}"
                )
                self.job_registry.update_job(
                    job_id,
                    status=JobStatus.timeout,
                    message="Processing timed out after 60 minutes",
                )
                return

            # Find the actual output files (pipeline may add timestamp)
            logger.debug(
                f"[WEB_SERVICE] Looking for output files - job_id: {job_id}, pattern: {job_id}_output*"
            )
            csv_files = list(self.tmp_dir.glob(f"{job_id}_output*.csv"))
            excel_files = list(self.tmp_dir.glob(f"{job_id}_output*.xlsx"))

            if not csv_files:
                logger.error(
                    f"[WEB_SERVICE] No CSV output file found - job_id: {job_id}, searched in: {self.tmp_dir}"
                )
                raise FileNotFoundError("No CSV output file found")

            if not excel_files:
                logger.error(
                    f"[WEB_SERVICE] No Excel output file found - job_id: {job_id}, searched in: {self.tmp_dir}"
                )
                raise FileNotFoundError("No Excel output file found")

            csv_output_path = csv_files[0]
            excel_output_path = excel_files[0]
            logger.info(
                f"[WEB_SERVICE] Found output files - job_id: {job_id}, csv: {csv_output_path}, excel: {excel_output_path}"
            )

            # Check file sizes and content
            try:
                csv_size = csv_output_path.stat().st_size
                excel_size = excel_output_path.stat().st_size
                logger.info(
                    f"[WEB_SERVICE] Output file stats - job_id: {job_id}, csv_size: {csv_size} bytes, excel_size: {excel_size} bytes"
                )
            except Exception as e:
                logger.warning(
                    f"[WEB_SERVICE] Could not get output file stats - job_id: {job_id}, error: {str(e)}"
                )

            total_time = time.time() - start_time
            logger.info(
                f"[WEB_SERVICE] Job processing completed successfully - job_id: {job_id}, total_time: {total_time:.2f}s"
            )
            self.job_registry.update_job(
                job_id,
                status=JobStatus.completed,
                percent=100,
                message="Processing completed successfully",
                output_file_path=str(csv_output_path),
                excel_output_file_path=str(excel_output_path),
            )

        except Exception as e:
            total_time = time.time() - start_time
            logger.error(
                f"[WEB_SERVICE] Job processing failed - job_id: {job_id}, total_time: {total_time:.2f}s, error: {str(e)}",
                exc_info=True,
            )
            self.job_registry.update_job(
                job_id,
                status=JobStatus.failed,
                message=f"Processing failed: {str(e)}",
                error=str(e),
            )

    def get_job_status(self, job_id: str) -> Optional[ProgressResponse]:
        """Get the current status of a processing job."""
        logger.debug(f"[WEB_SERVICE] Retrieving job status - job_id: {job_id}")
        job_info = self.job_registry.get_job(job_id)
        if not job_info:
            logger.debug(f"[WEB_SERVICE] Job not found in registry - job_id: {job_id}")
            return None

        logger.debug(
            f"[WEB_SERVICE] Job status retrieved - job_id: {job_id}, status: {job_info['status']}, percent: {job_info['percent']}%"
        )
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
        logger.info(f"[WEB_SERVICE] Generating results preview - job_id: {job_id}")

        job_info = self.job_registry.get_job(job_id)
        if not job_info or job_info["status"] != JobStatus.completed:
            logger.warning(
                f"[WEB_SERVICE] Cannot generate preview - job not found or not completed - job_id: {job_id}"
            )
            return None

        output_file_path = job_info.get("output_file_path")
        if not output_file_path or not os.path.exists(output_file_path):
            logger.error(
                f"[WEB_SERVICE] Output file not found - job_id: {job_id}, path: {output_file_path}"
            )
            return None

        try:
            logger.debug(
                f"[WEB_SERVICE] Reading CSV file for preview - job_id: {job_id}, path: {output_file_path}"
            )
            # Load configuration to get the CSV separator
            config = load_config(self.config_path)
            csv_separator = config["output"].get("csv_separator", ";")
            logger.debug(
                f"[WEB_SERVICE] Using CSV separator: '{csv_separator}' - job_id: {job_id}"
            )
            # Read CSV file with the configured separator
            df = pd.read_csv(output_file_path, sep=csv_separator)
            logger.info(
                f"[WEB_SERVICE] CSV loaded successfully - job_id: {job_id}, total_rows: {len(df)}, columns: {len(df.columns)}"
            )

            # Get first 10 rows
            preview_df = df.head(10)
            logger.debug(
                f"[WEB_SERVICE] Created preview dataframe - job_id: {job_id}, preview_rows: {len(preview_df)}"
            )

            # Helper function to safely convert pandas values to Pydantic-compatible strings
            def safe_str_convert(value):
                """Convert pandas values to strings, handling NaN and None values."""
                if pd.isna(value) or value is None:
                    return None
                return str(value)

            # Convert to list of AmendmentPreview objects
            preview_rows = []
            for _, row in preview_df.iterrows():
                preview_rows.append(
                    AmendmentPreview(
                        num_amdt=safe_str_convert(row.get("Num amdt")),
                        commentaires=safe_str_convert(row.get("Commentaires")),
                        allotissement=safe_str_convert(row.get("Allotissement")),
                        objet_amdt=safe_str_convert(row.get("Objet amdt")),
                        sort=safe_str_convert(row.get("Sort")),
                        reponse=safe_str_convert(row.get("Réponse")),
                        affectation_email=safe_str_convert(
                            row.get("Affectation (email)")
                        ),
                        affectation_nom=safe_str_convert(row.get("Affectation (nom)")),
                        entite_pilote=safe_str_convert(row.get("Entité Pilote")),
                        avis_du_gouvernement=safe_str_convert(
                            row.get("Avis du Gouvernement")
                        ),
                        groupe=safe_str_convert(row.get("Groupe")),
                        num_article=safe_str_convert(row.get("Num article")),
                        expose_amdt=safe_str_convert(row.get("Exposé amdt")),
                        corps_amdt=safe_str_convert(row.get("Corps amdt")),
                        mission=safe_str_convert(row.get("Mission")),
                    )
                )

            logger.info(
                f"[WEB_SERVICE] Preview generated successfully - job_id: {job_id}, total_rows: {len(df)}, preview_rows: {len(preview_rows)}"
            )
            return PreviewResponse(
                job_id=job_id,
                total_rows=len(df),
                preview_rows=preview_rows,
                columns=list(df.columns),
            )

        except Exception as e:
            logger.error(
                f"[WEB_SERVICE] Error reading results for preview - job_id: {job_id}, error: {str(e)}",
                exc_info=True,
            )
            return None

    def get_results_file_path(self, job_id: str) -> Optional[str]:
        """Get the path to the results CSV file for download."""
        logger.debug(f"[WEB_SERVICE] Retrieving results file path - job_id: {job_id}")

        job_info = self.job_registry.get_job(job_id)
        if not job_info or job_info["status"] != JobStatus.completed:
            logger.warning(
                f"[WEB_SERVICE] Cannot get file path - job not found or not completed - job_id: {job_id}"
            )
            return None

        file_path = job_info.get("output_file_path")
        logger.debug(
            f"[WEB_SERVICE] Results file path retrieved - job_id: {job_id}, path: {file_path}"
        )
        return file_path

    def get_excel_results_file_path(self, job_id: str) -> Optional[str]:
        """Get the path to the results Excel file for download."""
        logger.debug(
            f"[WEB_SERVICE] Retrieving Excel results file path - job_id: {job_id}"
        )

        job_info = self.job_registry.get_job(job_id)
        if not job_info or job_info["status"] != JobStatus.completed:
            logger.warning(
                f"[WEB_SERVICE] Cannot get Excel file path - job not found or not completed - job_id: {job_id}"
            )
            return None

        file_path = job_info.get("excel_output_file_path")
        logger.debug(
            f"[WEB_SERVICE] Excel results file path retrieved - job_id: {job_id}, path: {file_path}"
        )
        return file_path


# Global job registry instance
job_registry = InMemoryJobRegistry()
# Global service instance
web_processing_service = WebProcessingService(job_registry=job_registry)
