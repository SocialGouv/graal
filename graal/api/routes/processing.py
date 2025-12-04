"""
Processing API routes for GRAAL amendment processing.
"""

import logging
import logging.config

from fastapi import APIRouter, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from graal.api.models.requests import ProcessingRequest
from graal.api.models.responses import (
    ConfigFilesResponse,
    PreviewResponse,
    ProcessingResponse,
    ProgressResponse,
)
from graal.utils.s3_service import get_s3_service

logging.config.fileConfig("logging.conf")
router = APIRouter()


def get_web_processing_service():
    """Get the global web processing service instance."""
    from graal.api.main import web_processing_service

    return web_processing_service


@router.get("/config-files", response_model=ConfigFilesResponse)
async def list_config_files():
    """
    List available configuration files from S3.

    Returns:
        ConfigFilesResponse with list of available configuration files

    Raises:
        HTTPException: 503 if S3 is not available, 500 for other errors
    """
    logging.info("[API] Listing available configuration files")

    try:
        s3_service = get_s3_service()
        files = s3_service.list_available_config_files()

        logging.info(f"[API] Found {len(files)} configuration files")
        return ConfigFilesResponse(files=files, total=len(files))

    except Exception as e:
        logging.error(f"[API] Failed to list config files: {str(e)}")
        if "not enabled" in str(e).lower() or "not available" in str(e).lower():
            raise HTTPException(
                status_code=503, detail="S3 configuration service is not available"
            ) from e
        raise HTTPException(
            status_code=500, detail=f"Failed to list configuration files: {str(e)}"
        ) from e


@router.post("/process", response_model=ProcessingResponse)
async def process_amendments(file: UploadFile, request: str = Form(...)):  # noqa: C901
    """
    Upload and process a JSON file containing amendments.

    Args:
        file: JSON file containing amendments data
        request: JSON string containing ProcessingRequest data (see ProcessingRequest model)

    Returns:
        ProcessingResponse with job_id and initial status

    Raises:
        HTTPException: 400 for validation errors, 413 for file too large, 422 for invalid JSON

    Example request JSON:
        {
            "processing_config": {
                "origin_project": "PLF 2025",
                "allotment": {
                    "enabled": true,
                    "column": "Corps amdt",
                    "similarity_threshold": 0.999
                },
                "similarities_within_lectures": {
                    "enabled": false,
                    "column": "Exposé amdt",
                    "similarity_threshold": 0.8
                },
                "similarity_search": {
                    "enabled": false
                },
                "attribution": {
                    "enabled": true,
                    "project_name": "PLF"
                },
                "default_opinion": {
                    "enabled": false
                }
            }
        }
    """
    # Parse and validate the ProcessingRequest
    try:
        import json

        request_data = json.loads(request)
        processing_request = ProcessingRequest(**request_data)
    except json.JSONDecodeError as e:
        logging.warning(f"[API] Invalid JSON in request parameter: {str(e)}")
        raise HTTPException(
            status_code=400, detail="Invalid JSON in request parameter"
        ) from e
    except Exception as e:
        logging.warning(f"[API] Invalid ProcessingRequest: {str(e)}")
        raise HTTPException(
            status_code=400, detail=f"Invalid request data: {str(e)}"
        ) from e

    # Validate that at least one feature is enabled
    if not processing_request.processing_config.has_any_feature_enabled():
        logging.warning("[API] Processing request rejected - no features enabled")
        raise HTTPException(
            status_code=400,
            detail="At least one feature must be enabled to start processing",
        )

    # Validate config file exists in S3
    config_file = processing_request.config_file
    logging.info(f"[API] Validating config file: {config_file}")

    try:
        s3_service = get_s3_service()
        if not s3_service.validate_config_file_exists(config_file):
            logging.warning(f"[API] Config file not found in S3: {config_file}")
            raise HTTPException(
                status_code=404,
                detail=f"Configuration file '{config_file}' not found in S3",
            )
        logging.info(f"[API] Config file validated successfully: {config_file}")
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"[API] Failed to validate config file: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to validate configuration file: {str(e)}"
        ) from e

    logging.info(
        f"[API] Received file upload request - filename: {file.filename}, content_type: {file.content_type}, config_file: {config_file}"
    )

    if file.filename is None or file.filename == "":
        logging.warning("[API] File upload rejected - no filename provided")
        raise HTTPException(status_code=400, detail="No file uploaded")

    # Validate file type
    if not file.filename.endswith(".json"):
        logging.warning(
            f"[API] File upload rejected - invalid file type: {file.filename}"
        )
        raise HTTPException(status_code=422, detail="Only JSON files are supported")

    try:
        # Read file content
        logging.debug(f"[API] Reading file content for: {file.filename}")
        file_content = await file.read()
        file_size = len(file_content)
        logging.info(f"[API] File content read successfully - size: {file_size} bytes")

        # Start processing
        logging.info(f"[API] Starting processing service for file: {file.filename}")
        service = get_web_processing_service()
        response = await service.start_processing(
            file_content=file_content,
            filename=file.filename,
            processing_request=processing_request,
        )

        logging.info(
            f"[API] Processing job created successfully - job_id: {response.job_id}, filename: {file.filename}, status: {response.status}"
        )
        return response

    except ValueError as e:
        if "exceeds maximum" in str(e):
            logging.error(
                f"[API] File too large - filename: {file.filename}, error: {str(e)}"
            )
            raise HTTPException(status_code=413, detail=str(e)) from e
        else:
            logging.error(
                f"[API] File validation failed - filename: {file.filename}, error: {str(e)}"
            )
            raise HTTPException(status_code=422, detail=str(e)) from e
    except Exception as e:
        logging.error(
            f"[API] Unexpected error during processing start - filename: {file.filename}, error: {str(e)}",
            exc_info=True,
        )
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
    logging.debug(f"[API] Status request for job_id: {job_id}")

    service = get_web_processing_service()
    status = service.get_job_status(job_id)
    if not status:
        logging.warning(f"[API] Status request failed - job not found: {job_id}")
        raise HTTPException(status_code=404, detail="Job not found")

    logging.debug(
        f"[API] Status retrieved for job_id: {job_id}, status: {status.status}, progress: {status.percent}%"
    )
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
    logging.info(f"[API] Preview request for job_id: {job_id}")

    # Check if job exists and is completed
    service = get_web_processing_service()
    status = service.get_job_status(job_id)
    if not status:
        logging.warning(f"[API] Preview request failed - job not found: {job_id}")
        raise HTTPException(status_code=404, detail="Job not found")

    if status.status != "completed":
        logging.warning(
            f"[API] Preview request failed - job not completed: {job_id}, current status: {status.status}"
        )
        raise HTTPException(
            status_code=400,
            detail=f"Job is not completed. Current status: {status.status}",
        )

    # Get results preview
    logging.debug(f"[API] Generating results preview for job_id: {job_id}")
    preview = service.get_results_preview(job_id)
    if not preview:
        logging.error(f"[API] Failed to generate results preview for job_id: {job_id}")
        raise HTTPException(
            status_code=500, detail="Failed to generate results preview"
        )

    logging.info(
        f"[API] Preview generated successfully for job_id: {job_id}, total_rows: {preview.total_rows}, preview_rows: {len(preview.preview_rows)}"
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
    logging.info(f"[API] CSV download request for job_id: {job_id}")

    # Check if job exists and is completed
    service = get_web_processing_service()
    status = service.get_job_status(job_id)
    if not status:
        logging.warning(f"[API] Download request failed - job not found: {job_id}")
        raise HTTPException(status_code=404, detail="Job not found")

    if status.status != "completed":
        logging.warning(
            f"[API] Download request failed - job not completed: {job_id}, current status: {status.status}"
        )
        raise HTTPException(
            status_code=400,
            detail=f"Job is not completed. Current status: {status.status}",
        )

    # Get results file path
    logging.debug(f"[API] Retrieving CSV results file path for job_id: {job_id}")
    file_path = service.get_results_file_path(job_id)
    if not file_path:
        logging.error(f"[API] CSV results file not found for job_id: {job_id}")
        raise HTTPException(status_code=500, detail="Results file not found")

    logging.info(
        f"[API] Serving CSV download for job_id: {job_id}, file_path: {file_path}"
    )
    return FileResponse(
        path=file_path, filename=f"graal_results_{job_id}.csv", media_type="text/csv"
    )


@router.get("/results/{job_id}/download/excel")
async def download_excel_results(job_id: str):
    """
    Download the complete processing results as an Excel file.

    Args:
        job_id: Unique job identifier

    Returns:
        Excel file download

    Raises:
        HTTPException: 404 if job not found, 400 if job not completed
    """
    logging.info(f"[API] Excel download request for job_id: {job_id}")

    # Check if job exists and is completed
    service = get_web_processing_service()
    status = service.get_job_status(job_id)
    if not status:
        logging.warning(
            f"[API] Excel download request failed - job not found: {job_id}"
        )
        raise HTTPException(status_code=404, detail="Job not found")

    if status.status != "completed":
        logging.warning(
            f"[API] Excel download request failed - job not completed: {job_id}, current status: {status.status}"
        )
        raise HTTPException(
            status_code=400,
            detail=f"Job is not completed. Current status: {status.status}",
        )

    # Get Excel results file path
    logging.debug(f"[API] Retrieving Excel results file path for job_id: {job_id}")
    file_path = service.get_excel_results_file_path(job_id)
    if not file_path:
        logging.error(f"[API] Excel results file not found for job_id: {job_id}")
        raise HTTPException(status_code=500, detail="Excel results file not found")

    logging.info(
        f"[API] Serving Excel download for job_id: {job_id}, file_path: {file_path}"
    )
    return FileResponse(
        path=file_path,
        filename=f"graal_results_{job_id}.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
