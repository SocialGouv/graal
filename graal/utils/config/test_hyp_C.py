from pathlib import Path

from .base_config import InputFileConfig, ProjectConfig, create_timestamp, get_data_path


def get_test_hyp_C_config() -> ProjectConfig:
    json_configs: dict[Path, InputFileConfig] = {}

    excel_configs: dict[Path, InputFileConfig] = {
        get_data_path("exports_lectures/PLFSS 2025/PLFSS_2025_L1_AN_SP.xlsx"): {
            "default_processing_timestamp": create_timestamp(2024, 6, 1),
            "origin_project": "PLFSS 2025",
        },
    }

    return ProjectConfig(json_configs=json_configs, excel_configs=excel_configs)
