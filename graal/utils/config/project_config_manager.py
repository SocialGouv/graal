"""
Project configuration manager for amendment preprocessing.

This module provides functionality to load and combine configurations from different projects.
"""

from pathlib import Path
from typing import Dict, List, Optional

from graal.utils.config.base_config import InputFileConfig, ProjectConfig
from graal.utils.config.lfrss_config import get_lfrss_config
from graal.utils.config.placss_config import get_placss_config
from graal.utils.config.plf_config import get_plf_config
from graal.utils.config.plfss_config import get_plfss_config
from graal.utils.config.ppl_config import get_ppl_config
from graal.utils.config.test_hyp_A import get_test_hyp_A_config
from graal.utils.config.test_hyp_B import get_test_hyp_B_config
from graal.utils.config.test_hyp_C import get_test_hyp_C_config


class ProjectConfigManager:
    """Manages loading and combining project configurations."""

    AVAILABLE_PROJECTS = {
        "PLFSS": get_plfss_config,
        "PLACSS": get_placss_config,
        "LFRSS": get_lfrss_config,
        "PPL": get_ppl_config,
        "PLF": get_plf_config,
        "TEST_A": get_test_hyp_A_config,
        "TEST_B": get_test_hyp_B_config,
        "TEST_C": get_test_hyp_C_config,
    }

    @classmethod
    def get_project_configs(
        cls, project_names: Optional[List[str]] = None
    ) -> ProjectConfig:
        """Get combined configuration for specified projects.

        Args:
            project_names: List of project names to include. If None, includes all projects.
                         Valid names are: PLFSS, PLACSS, LFRSS, PPL, PLF

        Returns:
            Combined ProjectConfig containing all configurations from specified projects.
        """
        if project_names is None:
            project_names = list(cls.AVAILABLE_PROJECTS.keys())

        json_configs: Dict[Path, InputFileConfig] = {}
        excel_configs: Dict[Path, InputFileConfig] = {}

        for project_name in project_names:
            if project_name not in cls.AVAILABLE_PROJECTS:
                raise ValueError(
                    f"Unknown project: {project_name}. Valid projects are: {list(cls.AVAILABLE_PROJECTS.keys())}"
                )

            project_config = cls.AVAILABLE_PROJECTS[project_name]()
            json_configs.update(project_config.json_configs)
            excel_configs.update(project_config.excel_configs)

        return ProjectConfig(json_configs=json_configs, excel_configs=excel_configs)
