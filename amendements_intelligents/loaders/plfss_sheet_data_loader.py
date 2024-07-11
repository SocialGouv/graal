import pandas as pd


class PLFSSSheetDataLoader:
    def __init__(self, file_path):
        self.file_path = file_path
        self.excel_data = pd.read_excel(file_path, sheet_name=None)
        self.sheet_names = self.excel_data.keys()
        print(f"Sheet names in the excel file: {self.sheet_names}")

    def extract_sheet_data(self, sheet_name):
        print(f'Extracting PLFSS data from sheet "{sheet_name}"')
        if sheet_name in self.sheet_names:
            sheet_data = self.excel_data[sheet_name]
            df = pd.DataFrame(sheet_data.values, columns=sheet_data.iloc[0])
            df = df.iloc[1:]
        else:
            print(f"Sheet '{sheet_name}' not found.")
        return df

    def show_exploratory_analysis(self, plfss_df: pd.DataFrame) -> None:
        # Get the number of rows and columns
        num_rows, num_cols = plfss_df.shape
        print(f"Number of rows: {num_rows}")
        print(f"Number of columns: {num_cols}")

        # Get the column names
        column_names = plfss_df.columns.tolist()
        print("Column names:")
        print(column_names)

        # Calculate the ratio of missing values for each column
        missing_ratio = plfss_df.isnull().mean()

        # Print the missing ratio for each column
        print("Missing value ratio for each column:")
        print(missing_ratio * 100)

        # Calculate the length of each value in the 'Exposé des motifs' column
        lengths = plfss_df["Exposé des motifs"].dropna().apply(len)

        # Display the minimum, mean, and maximum length
        print("Analysis of 'Exposé des motifs':")
        print(f"Minimum length: {lengths.min()}")
        print(f"Mean length: {lengths.mean()}")
        print(f"Maximum length: {lengths.max()}")
