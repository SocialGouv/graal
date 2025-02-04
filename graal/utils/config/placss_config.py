"""
PLACSS-specific configuration for amendment preprocessing.
"""

from pathlib import Path
from .base_config import ProjectConfig, InputFileConfig, create_timestamp, get_data_path


def get_placss_config() -> ProjectConfig:
    """Get PLACSS project configuration."""

    json_configs: dict[Path, InputFileConfig] = {
        get_data_path(
            "exports_lectures/PLACSS 22/AN Séance 1ère lecture/lecture-an-16-1268-PO791932.json"
        ): {
            "default_processing_timestamp": create_timestamp(2022, 7, 1),
            "origin_project": "PLACSS 2021",
        },
        get_data_path(
            "exports_lectures/PLACSS 22/Sénat Séance 1ère lecture/lecture-senat-2022-2023-705-PO78718.json"
        ): {
            "default_processing_timestamp": create_timestamp(2022, 7, 1),
            "origin_project": "PLACSS 2021",
        },
    }

    excel_configs: dict[Path, InputFileConfig] = {}

    return ProjectConfig(json_configs=json_configs, excel_configs=excel_configs)
