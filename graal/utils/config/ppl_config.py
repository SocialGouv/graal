"""
PPL-specific configuration for amendment preprocessing.
"""

from pathlib import Path
from .base_config import ProjectConfig, InputFileConfig, create_timestamp, get_data_path


def get_ppl_config() -> ProjectConfig:
    """Get PPL project configuration."""

    json_configs: dict[Path, InputFileConfig] = {
        get_data_path(
            "exports_lectures/PPL LIOT 2023 abrogation réforme des retraites/Séance AN/lecture-an-16-1299-PO791932.json"
        ): {
            "default_processing_timestamp": create_timestamp(2023, 7, 1),
            "origin_project": "PPL LIOT abrogation réforme des retraites",
        },
    }

    excel_configs: dict[Path, InputFileConfig] = {
        get_data_path(
            "exports_lectures/PPL Retraites/2024/PPL_retraites_RN_BDD.xlsx"
        ): {
            "default_processing_timestamp": create_timestamp(2024, 10, 1),
            "origin_project": "PPL Retraites 2024",
        },
        get_data_path(
            "exports_lectures/PPL fin de vie 2024/BDD_Commission_PJL fin de vie.xlsx"
        ): {
            "default_processing_timestamp": create_timestamp(2024, 5, 18),
            "origin_project": "PPL Fin de vie 2024",
        },
    }

    return ProjectConfig(json_configs=json_configs, excel_configs=excel_configs)
