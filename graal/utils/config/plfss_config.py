"""
PLFSS-specific configuration for amendment preprocessing.
"""

from pathlib import Path
from .base_config import ProjectConfig, InputFileConfig, create_timestamp, get_data_path


def get_plfss_config() -> ProjectConfig:
    """Get PLFSS project configuration."""

    json_configs: dict[Path, InputFileConfig] = {
        get_data_path(
            "exports_lectures/PLFSS 2021 JSON/lecture-senat-2020-2021-101-PO78718.json"
        ): {
            "default_processing_timestamp": create_timestamp(2021, 7, 1),
            "origin_project": "PLFSS 2022",
        },
        get_data_path(
            "exports_lectures/PLFSS 2021 JSON/lecture-an-15-3551-PO717460.json"
        ): {
            "default_processing_timestamp": create_timestamp(2021, 7, 1),
            "origin_project": "PLFSS 2022",
        },
        get_data_path(
            "exports_lectures/PLFSS 2021 JSON/lecture-an-15-3397-PO717460.json"
        ): {
            "default_processing_timestamp": create_timestamp(2021, 7, 1),
            "origin_project": "PLFSS 2022",
        },
        get_data_path(
            "exports_lectures/PLFSS 2021 JSON/lecture-an-15-3397-PO420120.json"
        ): {
            "default_processing_timestamp": create_timestamp(2021, 7, 1),
            "origin_project": "PLFSS 2022",
        },
        get_data_path(
            "exports_lectures/PLFSS 2022 - JSON/lecture-senat-2021-2022-118-PO78718.json"
        ): {
            "default_processing_timestamp": create_timestamp(2022, 7, 1),
            "origin_project": "PLFSS 2023",
        },
        get_data_path(
            "exports_lectures/PLFSS 2022 - JSON/lecture-senat-2021-2022-189-PO78718.json"
        ): {
            "default_processing_timestamp": create_timestamp(2022, 7, 1),
            "origin_project": "PLFSS 2023",
        },
        get_data_path(
            "exports_lectures/PLFSS 2022 - JSON/lecture-an-15-4685-PO717460.json"
        ): {
            "default_processing_timestamp": create_timestamp(2022, 7, 1),
            "origin_project": "PLFSS 2023",
        },
        get_data_path(
            "exports_lectures/PLFSS 2022 - JSON/lecture-an-15-4523-PO717460.json"
        ): {
            "default_processing_timestamp": create_timestamp(2022, 7, 1),
            "origin_project": "PLFSS 2023",
        },
        get_data_path(
            "exports_lectures/PLFSS 2023/lecture-senat-2022-2023-96-PO78718.json"
        ): {
            "default_processing_timestamp": create_timestamp(2023, 7, 1),
            "origin_project": "PLFSS 2024",
        },
        get_data_path("exports_lectures/PLFSS 2023/lecture-an-16-274-PO791932.json"): {
            "default_processing_timestamp": create_timestamp(2023, 7, 1),
            "origin_project": "PLFSS 2024",
        },
        get_data_path("exports_lectures/PLFSS 2023/lecture-an-16-274-PO420120.json"): {
            "default_processing_timestamp": create_timestamp(2023, 7, 1),
            "origin_project": "PLFSS 2024",
        },
        get_data_path(
            "exports_lectures/PLFSS 2023/lecture-an-16-1682-PO791932 (2).json"
        ): {
            "default_processing_timestamp": create_timestamp(2023, 7, 1),
            "origin_project": "PLFSS 2024",
        },
        get_data_path("exports_lectures/PLFSS 2023/lecture-an-16-480-PO791932.json"): {
            "default_processing_timestamp": create_timestamp(2023, 7, 1),
            "origin_project": "PLFSS 2024",
        },
        get_data_path(
            "exports_lectures/Export PLFSS 2024/JSON/lecture-an-16-1682-PO420120.json"
        ): {
            "default_processing_timestamp": create_timestamp(2024, 7, 1),
            "origin_project": "PLFSS 2025",
        },
        get_data_path(
            "exports_lectures/Export PLFSS 2024/JSON/lecture-an-16-1875-PO791932.json"
        ): {
            "default_processing_timestamp": create_timestamp(2024, 7, 2),
            "origin_project": "PLFSS 2025",
        },
        get_data_path(
            "exports_lectures/Export PLFSS 2024/JSON/lecture-senat-2023-2024-77-PO78718.json"
        ): {
            "default_processing_timestamp": create_timestamp(2024, 7, 3),
            "origin_project": "PLFSS 2025",
        },
    }

    excel_configs: dict[Path, InputFileConfig] = {
        get_data_path(
            "exports_lectures/PLFSS 2025/BDD_AN_L1_SP_Amendements_copie_valeurs.xlsx"
        ): {
            "default_processing_timestamp": create_timestamp(2024, 10, 17),
            "origin_project": "PLFSS 2025",
        },
        get_data_path("exports_lectures/PLFSS 2025/BDD_PLFSS_2025_SENAT_L1_SP.xlsx"): {
            "default_processing_timestamp": create_timestamp(2024, 11, 20),
            "origin_project": "PLFSS 2025",
        },
    }

    return ProjectConfig(json_configs=json_configs, excel_configs=excel_configs)
