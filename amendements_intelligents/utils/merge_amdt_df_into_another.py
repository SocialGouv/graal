# This script enables us to seamlessly merge an existing CSV file of amendments that have already
# been processed in Signale with newly processed amendments from the pipeline.
# This script is particularly useful if any issues occur within the full pipeline,
# resulting in agents beginning work on amendments directly in Signale.
# Once the pipeline is repaired, we generate a new CSV for import into Signale.
# However, without this script, that import would overwrite prior work—a situation we aim to avoid.

import logging
import logging.config
import os

import pandas as pd
from pydantic import FilePath

from amendements_intelligents.utils.amendment_pre_processor import AmendmentPreProcessor

logging.config.fileConfig("logging.conf")

if __name__ == "__main__":
    DATA_FOLDER = os.getenv("DATA_FOLDER", "data")

    df_to_keep = AmendmentPreProcessor.load_amendments_json(
        input_files=[
            FilePath(
                f"{DATA_FOLDER}/exports_lectures/Export PLFSS 2024/JSON/lecture-an-16-1682-PO420120.json"
            )
        ]
    )
    df_to_keep = AmendmentPreProcessor.remap_columns_in_json_amendments(df_to_keep)

    df_to_overwrite = pd.read_csv(
        f"{DATA_FOLDER}/PLFSS_2025_oct_17.csv", delimiter=";", encoding="utf-8-sig"
    )

    # Set the "Allotissement" column in df_to_merge_in to the corresponding "Allotissement" in df_to_overwrite because that is the one column we want to keep
    df_to_keep = df_to_keep.merge(
        df_to_overwrite[["Num amdt", "Organe", "Lecture", "Allotissement"]],
        on=["Num amdt", "Organe", "Lecture"],
        how="left",
        suffixes=("", "_overwrite"),
    )

    # Update the "Allotissement" column in df_to_merge_in
    df_to_keep["Allotissement"] = df_to_keep["Allotissement_overwrite"]

    # Drop the temporary "Allotissement_overwrite" column
    df_to_keep.drop(columns=["Allotissement_overwrite"], inplace=True)

    # Merge the dataframes on the specified primary keys
    merged_df = pd.merge(
        df_to_overwrite,
        df_to_keep,
        on=["Num amdt", "Organe", "Lecture"],
        how="right",
        suffixes=("_overwrite", ""),
    )

    # Only overwrite if the value in the cell of df_to_keep is not "", not NaN, and not None
    for column in df_to_keep.columns:
        if column not in ["Num amdt", "Organe", "Lecture"]:
            overwrite_column = f"{column}_overwrite"
            # Pass `column` and `overwrite_column` as default arguments to the lambda function
            merged_df[column] = merged_df.apply(
                lambda row, col=column, overwrite_col=overwrite_column: row[col]
                if pd.notna(row[col]) and row[col] != "" and row[col] is not None
                else row[overwrite_col],
                axis=1,
            )

    # Drop the columns with the '_overwrite' suffix
    columns_to_drop = [col for col in merged_df.columns if col.endswith("_overwrite")]
    merged_df.drop(columns=columns_to_drop, inplace=True)

    # Save the merged dataframe back to df_to_overwrite
    df_to_overwrite = merged_df

    # Save the updated dataframe to a CSV file
    csv_file_path = f"{DATA_FOLDER}/PLFSS_2025_updated.csv"
    df_to_overwrite.to_csv(
        csv_file_path,
        sep=";",
        encoding="utf-8-sig",
        index=False,
    )
    logging.info(f"CSV file saved: {csv_file_path}")

    # Save the updated dataframe to an Excel file
    excel_file_path = f"{DATA_FOLDER}/PLFSS_2025_updated.xlsx"
    df_to_overwrite.to_excel(
        excel_file_path,
        index=False,
    )
    logging.info(f"Excel file saved: {excel_file_path}")
