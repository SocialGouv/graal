"""
File handlers for loading amendment files of different types.

This module implements the file handler pattern to support loading amendments
from various file formats (JSON, Excel, etc.) without coupling the main
processing logic to specific file types.
"""

import logging
from abc import ABC, abstractmethod
from pathlib import Path

import pandas as pd

from graal.utils.amendment_pre_processor import AmendmentPreProcessor
from graal.utils.config.base_config import InputFileConfig

logger = logging.getLogger(__name__)


class AmendmentFileHandler(ABC):
    """Abstract base class for handling different amendment file types."""

    @abstractmethod
    def load_amendments(
        self,
        file_configs: dict[Path, InputFileConfig],
    ) -> pd.DataFrame:
        """
        Load amendments from files.

        Args:
            file_configs: Configuration for each file.

        Returns:
            DataFrame containing loaded amendments.
        """
        pass

    @abstractmethod
    def get_supported_extensions(self) -> tuple[str, ...]:
        """
        Return tuple of supported file extensions (lowercase with dot).

        Returns:
            Tuple of supported extensions, e.g., ('.json',) or ('.xlsx', '.xls')
        """
        pass


class JsonFileHandler(AmendmentFileHandler):
    """Handler for JSON amendment files."""

    def load_amendments(
        self,
        file_configs: dict[Path, InputFileConfig],
    ) -> pd.DataFrame:
        """Load amendments from JSON files."""
        return AmendmentPreProcessor.load_amendments_json(
            list(file_configs.keys()), file_configs
        )

    def get_supported_extensions(self) -> tuple[str, ...]:
        """JSON files have .json extension."""
        return (".json",)


class ExcelFileHandler(AmendmentFileHandler):
    """Handler for Excel amendment files."""

    def load_amendments(
        self,
        file_configs: dict[Path, InputFileConfig],
    ) -> pd.DataFrame:
        """Load amendments from Excel files."""
        return AmendmentPreProcessor.load_amendments_excel(
            list(file_configs.keys()), file_configs
        )

    def get_supported_extensions(self) -> tuple[str, ...]:
        """Excel files can have .xlsx or .xls extensions."""
        return (".xlsx", ".xls")


class AmendmentFileHandlerRegistry:
    """Registry for mapping file extensions to handlers."""

    def __init__(self):
        """Initialize the registry with default handlers."""
        self._handlers: dict[str, AmendmentFileHandler] = {}
        self._register_default_handlers()

    def _register_default_handlers(self) -> None:
        """Register the default file handlers."""
        self.register_handler(JsonFileHandler())
        self.register_handler(ExcelFileHandler())

    def register_handler(self, handler: AmendmentFileHandler) -> None:
        """
        Register a file handler for its supported extensions.

        Args:
            handler: The file handler to register.
        """
        for ext in handler.get_supported_extensions():
            self._handlers[ext.lower()] = handler

    def get_handler(self, file_path: Path) -> AmendmentFileHandler | None:
        """
        Get the appropriate handler for a file based on its extension.

        Args:
            file_path: Path to the file.

        Returns:
            The appropriate handler, or None if no handler supports the file.
        """
        ext = file_path.suffix.lower()
        return self._handlers.get(ext)

    def group_files_by_handler(
        self,
        file_configs: dict[Path, InputFileConfig],
    ) -> dict[AmendmentFileHandler, dict[Path, InputFileConfig]]:
        """
        Group files by their handler type.

        Args:
            file_configs: Dictionary mapping file paths to their configurations.

        Returns:
            Dictionary mapping handlers to their file configurations.
        """
        grouped: dict[AmendmentFileHandler, dict[Path, InputFileConfig]] = {}

        for file_path, config in file_configs.items():
            handler = self.get_handler(file_path)
            if handler is not None:
                if handler not in grouped:
                    grouped[handler] = {}
                grouped[handler][file_path] = config

        return grouped
