"""
Base configuration file for amendment preprocessing.

This module contains the base configuration structure and utility functions
for loading project-specific amendment configurations.
"""

from datetime import datetime
from pathlib import Path
from typing import Dict, TypedDict


class InputFileConfig(TypedDict):
    default_processing_timestamp: int
    origin_project: str


class ProjectConfig:
    def __init__(
        self,
        json_configs: Dict[Path, InputFileConfig],
        excel_configs: Dict[Path, InputFileConfig],
    ):
        self.json_configs = json_configs
        self.excel_configs = excel_configs


def create_timestamp(year: int, month: int, day: int) -> int:
    """Create a timestamp from date components."""
    return int(datetime(year, month=month, day=day).timestamp())


# Base data folder configuration
DATA_FOLDER = "data"


def get_data_path(path: str) -> Path:
    """Get full path for data files."""
    return Path(f"{DATA_FOLDER}/{path}")
