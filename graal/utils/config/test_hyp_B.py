from pathlib import Path

from .base_config import InputFileConfig, ProjectConfig, create_timestamp, get_data_path


def get_test_hyp_B_config() -> ProjectConfig:
    json_configs: dict[Path, InputFileConfig] = {}

    excel_configs: dict[Path, InputFileConfig] = {
        get_data_path("exports_lectures/PLFSS 2024/PLFSS_2024_L1_AN_CAS.xlsx"): {
            "default_processing_timestamp": create_timestamp(2023, 6, 1),
            "origin_project": "PLFSS 2024",
        },
    }

    return ProjectConfig(json_configs=json_configs, excel_configs=excel_configs)
