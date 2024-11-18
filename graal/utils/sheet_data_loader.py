import logging

import pandas as pd


class SheetDataLoader:
    def __init__(self, file_path):
        self.file_path = file_path
        self.excel_data = pd.read_excel(file_path, sheet_name=None)
        self.sheet_names = self.excel_data.keys()
        logging.info(f"Sheet names in the excel file: {self.sheet_names}")

    def extract_sheet_data(self, sheet_name):
        logging.info(f'Extracting data from sheet "{sheet_name}"')
        if sheet_name in self.sheet_names:
            sheet_data = self.excel_data[sheet_name]
        else:
            logging.info(f"Sheet '{sheet_name}' not found.")
        return sheet_data
