import logging
import logging.config
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from graal.api.models.responses import (
    JobStatus,
)

logging.config.fileConfig("logging.conf")


class JobRegistry(ABC):
    """Interface for job registry."""

    @abstractmethod
    def create_job(self, job_id: str, input_file_path: str) -> None:
        pass

    @abstractmethod
    def update_job(self, job_id: str, **kwargs) -> None:
        pass

    @abstractmethod
    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    def delete_job(self, job_id: str) -> None:
        pass


class InMemoryJobRegistry(JobRegistry):
    """In-memory job registry to track processing status."""

    def __init__(self):
        self._jobs: Dict[str, Dict[str, Any]] = {}

    def create_job(self, job_id: str, input_file_path: str) -> None:
        """Create a new job entry."""
        self._jobs[job_id] = {
            "status": JobStatus.queued,
            "percent": 0,
            "message": "Job queued for processing",
            "started_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "input_file_path": input_file_path,
            "output_file_path": None,
            "error": None,
        }

    def update_job(self, job_id: str, **kwargs) -> None:
        """Update job status and other fields."""
        if job_id in self._jobs:
            self._jobs[job_id].update(kwargs)
            self._jobs[job_id]["updated_at"] = datetime.now(timezone.utc)

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job information."""
        return self._jobs.get(job_id)

    def delete_job(self, job_id: str) -> None:
        """Delete job from registry."""
        if job_id in self._jobs:
            del self._jobs[job_id]
