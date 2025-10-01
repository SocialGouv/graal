import logging
from pathlib import Path
from typing import Optional, Union

import pandas as pd

from graal.utils.s3_config_service import get_s3_config_service


class SheetDataLoader:
    def __init__(self, file_path: Union[str, Path], force_local: bool = False):
        """Initialize SheetDataLoader with support for S3 configuration files.

        Args:
            file_path: Path to the Excel file or configuration filename
            force_local: If True, always use local files even if S3 is available
        """
        self.file_path = file_path
        self.force_local = force_local
        self.excel_data = self._load_excel_data()
        self.sheet_names = self.excel_data.keys()
        logging.info(f"Sheet names in the excel file: {self.sheet_names}")

    def _load_excel_data(self) -> dict[str, pd.DataFrame]:
        """Load Excel data from S3 or local filesystem.

        Returns:
            dict[str, pd.DataFrame]: Dictionary mapping sheet names to DataFrames.
        """
        # Convert file_path to string for processing
        file_path_str = str(self.file_path)

        # Try S3 for configuration files if not forced to use local
        if not self.force_local:
            s3_service = get_s3_config_service()
            if s3_service.is_s3_enabled():
                try:
                    logging.info(
                        f"Attempting to load configuration from S3: {file_path_str}"
                    )
                    return s3_service.load_config_excel(file_path_str)
                except Exception as e:
                    logging.warning(
                        f"Failed to load from S3, falling back to local: {e}"
                    )

        # Fallback to local file loading
        logging.info(f"Loading Excel file from local path: {file_path_str}")
        return pd.read_excel(file_path_str, sheet_name=None)

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
