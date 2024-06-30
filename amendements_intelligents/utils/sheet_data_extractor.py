import pandas as pd


class SheetDataExtractor:
    def __init__(self, file_path):
        self.file_path = file_path
        self.xlsm_data = pd.read_excel(file_path, sheet_name=None)
        self.sheet_names = self.xlsm_data.keys()

    def extract_sheet_data(self, sheet_name):
        if sheet_name in self.sheet_names:
            sheet_data = self.xlsm_data[sheet_name]
            df = pd.DataFrame(sheet_data.values, columns=sheet_data.iloc[0])
            df = df.iloc[1:]
            return df
        else:
            print(f"Sheet '{sheet_name}' not found.")
            return None

    def save_sheet_data_as_json(self, sheet_name, output_path):
        df = self.extract_sheet_data(sheet_name)
        if df is not None:
            df.to_json(output_path, orient="records", index=False)
            print(f"Sheet '{sheet_name}' data saved as JSON: {output_path}")
