"""
LFRSS-specific configuration for amendment preprocessing.
"""

from pathlib import Path
from .base_config import ProjectConfig, InputFileConfig, create_timestamp, get_data_path


def get_lfrss_config() -> ProjectConfig:
    """Get LFRSS project configuration."""

    json_configs: dict[Path, InputFileConfig] = {
        get_data_path("exports_lectures/LFRSS 2023/lecture-an-16-760-PO791932.json"): {
            "default_processing_timestamp": create_timestamp(2023, 7, 1),
            "origin_project": "LFRSS 2023",
        },
        get_data_path("exports_lectures/LFRSS 2023/lecture-an-16-760-PO420120.json"): {
            "default_processing_timestamp": create_timestamp(2023, 7, 1),
            "origin_project": "LFRSS 2023",
        },
        get_data_path(
            "exports_lectures/LFRSS 2023/lecture-senat-2022-2023-368-PO78718.json"
        ): {
            "default_processing_timestamp": create_timestamp(2023, 7, 1),
            "origin_project": "LFRSS 2023",
        },
    }

    excel_configs: dict[Path, InputFileConfig] = {}

    return ProjectConfig(json_configs=json_configs, excel_configs=excel_configs)
