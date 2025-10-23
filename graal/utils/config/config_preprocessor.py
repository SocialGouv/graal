"""
Configuration preprocessor for GRAAL.

This module handles preprocessing of configuration files, including:
- Environment variable substitution
- Path resolution and validation
- Config value normalization
"""

import copy
import logging
import logging.config
import os
import re
from pathlib import Path
from typing import Any, Dict

logging.config.fileConfig("logging.conf")


class ConfigPreprocessor:
    """
    Preprocesses configuration dictionaries by resolving environment variables,
    validating paths, and normalizing values.
    """

    # Pattern to match environment variable placeholders like ${VAR_NAME}
    ENV_VAR_PATTERN = re.compile(r"\$\{([^}]+)\}")

    def __init__(self, validate_paths: bool = True):
        """
        Initialize the config preprocessor.

        Args:
            validate_paths: Whether to validate that resolved paths exist
        """
        self.validate_paths = validate_paths

    def preprocess_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Preprocess the entire configuration dictionary.

        Args:
            config: Raw configuration dictionary

        Returns:
            Preprocessed configuration dictionary with resolved variables

        Raises:
            ValueError: If required environment variables are missing
        """
        logging.info("Starting configuration preprocessing")

        # Deep copy to avoid modifying the original
        preprocessed_config = copy.deepcopy(config)

        # Recursively process all values in the config
        self._process_dict_recursive(preprocessed_config)

        logging.info("Configuration preprocessing completed")
        return preprocessed_config

    def _process_dict_recursive(self, obj: Any) -> None:
        """
        Recursively process a dictionary or list, resolving environment variables.
        Modifies the object in place.
        """
        if isinstance(obj, dict):
            for key, value in obj.items():
                if isinstance(value, str):
                    obj[key] = self._resolve_environment_variables(value)
                elif isinstance(value, (dict, list)):
                    self._process_dict_recursive(value)
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                if isinstance(item, str):
                    obj[i] = self._resolve_environment_variables(item)
                elif isinstance(item, (dict, list)):
                    self._process_dict_recursive(item)

    def _resolve_environment_variables(self, value: str) -> str:
        """
        Resolve environment variables in a string value.

        Args:
            value: String that may contain ${VAR_NAME} placeholders

        Returns:
            String with environment variables resolved

        Raises:
            ValueError: If a required environment variable is not set
        """

        def replace_env_var(match):
            var_name = match.group(1)
            env_value = os.environ.get(var_name)

            if env_value is None:
                raise ValueError(
                    f"Environment variable '{var_name}' is required but not set. "
                    f"Found in config value: '{value}'"
                )

            logging.debug(f"Resolved ${{{var_name}}} -> {env_value}")
            return env_value

        resolved_value = self.ENV_VAR_PATTERN.sub(replace_env_var, value)

        # If this looks like a file path and validation is enabled, check if it exists
        if self.validate_paths and self._is_file_path(resolved_value):
            self._validate_path(resolved_value, original_value=value)

        return resolved_value

    def _is_file_path(self, value: str) -> bool:
        """
        Determine if a string value represents a file path.

        This is a heuristic check - we consider it a path if:
        - It contains path separators
        - It has a file extension (but not just a number)
        - It starts with common path prefixes
        """
        if not value:
            return False

        # Check for path separators
        if "/" in value or "\\" in value:
            return True

        # Check for common path prefixes
        path_prefixes = ["~", "./", "../", "/"]
        if any(value.startswith(prefix) for prefix in path_prefixes):
            return True

        # Check for file extensions, but exclude pure numbers
        if "." in value and not value.replace(".", "").replace("-", "").isdigit():
            # Check if it looks like a file extension
            extension = value.split(".")[-1]
            if len(extension) <= 5 and extension.isalpha():
                return True

        return False

    def _validate_path(self, resolved_path: str, original_value: str) -> None:
        """
        Validate that a resolved path exists.

        Args:
            resolved_path: The path after environment variable resolution
            original_value: The original config value (for error messages)
        """
        path = Path(resolved_path)

        # For template paths (containing % formatting), skip validation
        if "%" in resolved_path:
            logging.debug(f"Skipping validation for template path: {resolved_path}")
            return

        # Check if path exists (file or directory)
        if not path.exists():
            # For some paths, the parent directory should exist even if the file doesn't
            parent = path.parent
            if parent.exists():
                logging.debug(
                    f"Path doesn't exist but parent directory does: {resolved_path}"
                )
                return

            logging.warning(
                f"Resolved path does not exist: {resolved_path} "
                f"(from config value: {original_value})"
            )
