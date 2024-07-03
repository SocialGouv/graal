def perform_plfss_exploratory_analysis(df) -> None:
    # Get the number of rows and columns
    num_rows, num_cols = df.shape
    print(f"Number of rows: {num_rows}")
    print(f"Number of columns: {num_cols}")

    # Get the column names
    column_names = df.columns.tolist()
    print("Column names:")
    print(column_names)

    # Calculate the ratio of missing values for each column
    missing_ratio = df.isnull().mean()

    # Print the missing ratio for each column
    print("Missing value ratio for each column:")
    print(missing_ratio * 100)

    # Calculate the length of each value in the 'Exposé des motifs' column
    lengths = df["Exposé des motifs"].dropna().apply(len)

    # Display the minimum, mean, and maximum length
    print("Analysis of 'Exposé des motifs':")
    print(f"Minimum length: {lengths.min()}")
    print(f"Mean length: {lengths.mean()}")
    print(f"Maximum length: {lengths.max()}")
