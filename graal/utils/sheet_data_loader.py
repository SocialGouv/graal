import logging
from pathlib import Path
from typing import Optional, Union

import pandas as pd

from graal.utils.s3.s3_service import get_s3_service


class SheetDataLoader:
    """Async-compatible loader for Excel configuration files from S3.

    Usage:
        loader = await SheetDataLoader.create(file_path)
    """

    def __init__(
        self, file_path: Union[str, Path], excel_data: dict[str, pd.DataFrame]
    ):
        """Private constructor. Use SheetDataLoader.create() instead.

        Args:
            file_path: Path to the Excel file or configuration filename
            excel_data: Pre-loaded Excel data
        """
        self.file_path = file_path
        self.excel_data = excel_data
        self.sheet_names = self.excel_data.keys()
        logging.info(f"Sheet names in the excel file: {self.sheet_names}")

    @classmethod
    async def create(cls, file_path: Union[str, Path]) -> "SheetDataLoader":
        """Create a SheetDataLoader instance asynchronously.

        Args:
            file_path: Path to the Excel file or configuration filename

        Returns:
            SheetDataLoader instance with loaded data
        """
        excel_data = await cls._load_excel_data(file_path)
        return cls(file_path, excel_data)

    @staticmethod
    async def _load_excel_data(file_path: Union[str, Path]) -> dict[str, pd.DataFrame]:
        """Load Excel data from S3 asynchronously.

        Returns:
            dict[str, pd.DataFrame]: Dictionary mapping sheet names to DataFrames.

        Raises:
            Exception: If S3 is not available or file cannot be loaded.
        """
        # Convert file_path to string for processing
        file_path_str = str(file_path)

        # Load from S3 using the S3 config service
        s3_service = get_s3_service()
        logging.info(f"Loading configuration from S3: {file_path_str}")
        return await s3_service.config.load_config_excel(file_path_str)

    def extract_sheet_data(self, sheet_name: str) -> Optional[pd.DataFrame]:
        """Extract data from a specific sheet.

        Args:
            sheet_name: Name of the sheet to extract.

        Returns:
            pd.DataFrame or None: The sheet data if found, None otherwise.
        """
        logging.info(f'Extracting data from sheet "{sheet_name}"')
        if sheet_name in self.sheet_names:
            sheet_data = self.excel_data[sheet_name]
            return sheet_data
        else:
            logging.info(f"Sheet '{sheet_name}' not found.")
            return None
