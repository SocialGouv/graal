"""
Processing API routes for GRAAL amendment processing.
"""

import logging

from fastapi import APIRouter, HTTPException, UploadFile
from fastapi.responses import FileResponse

from graal.api.models.responses import (
    PreviewResponse,
    ProcessingResponse,
    ProgressResponse,
)
from graal.api.services.web_processing_service import web_processing_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/process", response_model=ProcessingResponse)
async def process_amendments(file: UploadFile):
    """
    Upload and process a JSON file containing amendments.

    Args:
        file: JSON file containing amendments data

    Returns:
        ProcessingResponse with job_id and initial status

    Raises:
        HTTPException: 400 for validation errors, 413 for file too large, 422 for invalid JSON
    """
    if file.filename is None or file.filename == "":
        raise HTTPException(status_code=400, detail="No file uploaded")

    # Validate file type
    if not file.filename.endswith(".json"):
        raise HTTPException(status_code=422, detail="Only JSON files are supported")

    try:
        # Read file content
        file_content = await file.read()

        # Start processing
        response = await web_processing_service.start_processing(
            file_content=file_content, filename=file.filename
        )

        logger.info(
            f"Started processing job {response.job_id} for file {file.filename}"
        )
        return response

    except ValueError as e:
        if "exceeds maximum" in str(e):
            raise HTTPException(status_code=413, detail=str(e)) from e
        else:
            raise HTTPException(status_code=422, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Error starting processing: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.get("/status/{job_id}", response_model=ProgressResponse)
async def get_processing_status(job_id: str):
    """
    Get the current processing status of a job.

    Args:
        job_id: Unique job identifier

    Returns:
        ProgressResponse with current status and progress

    Raises:
        HTTPException: 404 if job not found
    """
    status = web_processing_service.get_job_status(job_id)
    if not status:
        raise HTTPException(status_code=404, detail="Job not found")

    return status


@router.get("/results/{job_id}/preview", response_model=PreviewResponse)
async def get_results_preview(job_id: str):
    """
    Get a preview of the processing results (first 10 rows).

    Args:
        job_id: Unique job identifier

    Returns:
        PreviewResponse with first 10 rows of results

    Raises:
        HTTPException: 404 if job not found, 400 if job not completed
    """
    # Check if job exists and is completed
    status = web_processing_service.get_job_status(job_id)
    if not status:
        raise HTTPException(status_code=404, detail="Job not found")

    if status.status != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Job is not completed. Current status: {status.status}",
        )

    # Get results preview
    preview = web_processing_service.get_results_preview(job_id)
    if not preview:
        raise HTTPException(
            status_code=500, detail="Failed to generate results preview"
        )

    return preview


@router.get("/results/{job_id}/download")
async def download_results(job_id: str):
    """
    Download the complete processing results as a CSV file.

    Args:
        job_id: Unique job identifier

    Returns:
        CSV file download

    Raises:
        HTTPException: 404 if job not found, 400 if job not completed
    """
    # Check if job exists and is completed
    status = web_processing_service.get_job_status(job_id)
    if not status:
        raise HTTPException(status_code=404, detail="Job not found")

    if status.status != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Job is not completed. Current status: {status.status}",
        )

    # Get results file path
    file_path = web_processing_service.get_results_file_path(job_id)
    if not file_path:
        raise HTTPException(status_code=500, detail="Results file not found")

    return FileResponse(
        path=file_path, filename=f"graal_results_{job_id}.csv", media_type="text/csv"
    )
