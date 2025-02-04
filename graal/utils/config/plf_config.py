"""
PLF-specific configuration for amendment preprocessing.
"""

from pathlib import Path
from .base_config import ProjectConfig, InputFileConfig, create_timestamp, get_data_path


def get_plf_config() -> ProjectConfig:
    """Get PLF project configuration."""

    json_configs: dict[Path, InputFileConfig] = {}

    excel_configs: dict[Path, InputFileConfig] = {
        get_data_path("exports_lectures/PLF 2024/BDD_PLF_2024_SEN_L1_SP.xlsx"): {
            "default_processing_timestamp": create_timestamp(2023, 10, 1),
            "origin_project": "PLF 2024",
        },
        get_data_path(
            "exports_lectures/PLF 2025/BDD_PLF_2025_AN_L1_COM_Affaires_sociales.xlsx"
        ): {
            "default_processing_timestamp": create_timestamp(2024, 10, 1),
            "origin_project": "PLF 2025",
        },
        get_data_path(
            "exports_lectures/PLF 2025/BDD_PLF_2025_AN_L1_COM_Finances.xlsx"
        ): {
            "default_processing_timestamp": create_timestamp(2024, 11, 1),
            "origin_project": "PLF 2025",
        },
        get_data_path("exports_lectures/PLF 2025/BDD_PLF_2025_AN_L1_SP.xlsx"): {
            "default_processing_timestamp": create_timestamp(2024, 12, 1),
            "origin_project": "PLF 2025",
        },
    }

    return ProjectConfig(json_configs=json_configs, excel_configs=excel_configs)
