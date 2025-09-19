"""
API request models.
"""

from pydantic import BaseModel


class ProcessingRequest(BaseModel):
    """Request model for processing amendments."""

    # For file uploads, we'll use FastAPI's UploadFile directly in the endpoint
    pass
