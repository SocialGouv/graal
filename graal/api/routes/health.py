"""
Health check API routes.
"""

from datetime import datetime, timezone

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    """
    Health check endpoint.

    Returns the current status and timestamp of the API.
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc),
        "service": "GRAAL Web API",
        "version": "1.0.0",
    }
