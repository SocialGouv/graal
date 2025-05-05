"""
Project configuration manager for amendment preprocessing.

This module provides functionality to load and combine configurations from different projects.
"""

import os
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import yaml

from graal.utils.config.base_config import (
    InputFileConfig,
    ProjectConfig,
    create_timestamp,
    get_data_path,
)


class ProjectConfigManager:
    """Manages loading and combining project configurations."""

    # Path to the YAML configuration file
    CONFIG_FILE_PATH = os.path.join("config", "db_amendments/projects.yml")

    # This will be populated with functions that load configs from YAML
    AVAILABLE_PROJECTS: dict[str, Callable[[], ProjectConfig]] = {}

    @classmethod
    def get_available_projects(cls) -> dict[str, Callable[[], ProjectConfig]]:
        """Get a list of available project names.

        Returns:
            List of project names.
        """
        if not cls.AVAILABLE_PROJECTS:
            cls.AVAILABLE_PROJECTS = cls._load_yaml_config()
        return cls.AVAILABLE_PROJECTS

    @classmethod
    def _load_yaml_config(cls) -> dict[str, Callable[[], ProjectConfig]]:
        """Load project configurations from YAML file.

        Returns:
            Dictionary mapping project names to functions that return ProjectConfig objects.
        """
        config_functions: dict[str, Callable[[], ProjectConfig]] = {}

        # Check if the YAML file exists
        if not os.path.exists(cls.CONFIG_FILE_PATH):
            raise FileNotFoundError(
                f"Configuration file not found: {cls.CONFIG_FILE_PATH}"
            )

        try:
            with open(cls.CONFIG_FILE_PATH, "r") as file:
                config_data = yaml.safe_load(file)

            if not config_data or "projects" not in config_data:
                raise ValueError(f"Invalid configuration file: {cls.CONFIG_FILE_PATH}")

            # Create a function for each project in the YAML file
            for project_name, project_data in config_data["projects"].items():
                # Create a closure to capture the current value of project_data
                def make_config_getter(
                    data: Dict[str, Any],
                ) -> Callable[[], ProjectConfig]:
                    return lambda: cls._create_project_config_from_yaml(data)

                config_functions[project_name] = make_config_getter(project_data)

            return config_functions
        except FileNotFoundError as e:
            print(f"Configuration file not found: {e}")
            raise
        except yaml.YAMLError as e:
            print(f"Invalid YAML format in configuration file: {e}")
            raise
        except Exception as e:
            print(f"Unexpected error loading YAML config: {e}")
            raise

    @classmethod
    def _create_project_config_from_yaml(
        cls, project_data: Dict[str, Any]
    ) -> ProjectConfig:
        """Create a ProjectConfig object from YAML data.

        Args:
            project_data: Dictionary containing project configuration data from YAML.

        Returns:
            ProjectConfig object.
        """
        json_configs: dict[Path, InputFileConfig] = {}
        excel_configs: dict[Path, InputFileConfig] = {}

        # Process JSON configs
        for config in project_data.get("json_configs", []):
            path = config.get("path", "")
            timestamp_data = config.get("default_processing_timestamp", {})
            timestamp = create_timestamp(
                timestamp_data.get("year"),
                timestamp_data.get("month"),
                timestamp_data.get("day"),
            )
            origin_project = config.get("origin_project", "")

            json_configs[get_data_path(path)] = {
                "default_processing_timestamp": timestamp,
                "origin_project": origin_project,
            }

        # Process Excel configs
        for config in project_data.get("excel_configs", []):
            path = config.get("path", "")
            timestamp_data = config.get("default_processing_timestamp", {})
            timestamp = create_timestamp(
                timestamp_data.get("year"),
                timestamp_data.get("month"),
                timestamp_data.get("day"),
            )
            origin_project = config.get("origin_project", "")

            excel_configs[get_data_path(path)] = {
                "default_processing_timestamp": timestamp,
                "origin_project": origin_project,
            }

        return ProjectConfig(json_configs=json_configs, excel_configs=excel_configs)

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
        # Initialize AVAILABLE_PROJECTS if it's empty
        cls.AVAILABLE_PROJECTS = cls.get_available_projects()

        if project_names is None:
            project_names = list(cls.AVAILABLE_PROJECTS.keys())

        json_configs: dict[Path, InputFileConfig] = {}
        excel_configs: dict[Path, InputFileConfig] = {}

        for project_name in project_names:
            if project_name not in cls.AVAILABLE_PROJECTS:
                raise ValueError(
                    f"Unknown project: {project_name}. Valid projects are: {list(cls.AVAILABLE_PROJECTS.keys())}"
                )

            project_config = cls.AVAILABLE_PROJECTS[project_name]()
            json_configs.update(project_config.json_configs)
            excel_configs.update(project_config.excel_configs)

        return ProjectConfig(json_configs=json_configs, excel_configs=excel_configs)
