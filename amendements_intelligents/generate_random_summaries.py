import argparse
import os

import pandas as pd

from amendements_intelligents.summary.summary_generator_clients import (
    SummaryGeneratorOllamaClient,
)
from amendements_intelligents.utils.plfss_pre_processor import PLFSSPreProcessor
from amendements_intelligents.utils.plfss_sheet_data_loader import PLFSSSheetDataLoader

DATA_FOLDER = os.getenv("DATA_FOLDER")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--plfss_excel_path", default=f"{DATA_FOLDER}/aled.xlsm")
    parser.add_argument(
        "--object_samples_csv_path",
        default=f"{DATA_FOLDER}/echantillon_objets_amendements.csv",
    )
    parser.add_argument("--sheet_name", default="PLFSS 2024")
    parser.add_argument("--nb_results", type=int, default=10)
    args = parser.parse_args()

    plfss_excel_path = args.plfss_excel_path
    object_samples_csv_path = args.object_samples_csv_path
    sheet_name = args.sheet_name
    nb_results = args.nb_results

    data_extractor = PLFSSSheetDataLoader(plfss_excel_path)
    df = data_extractor.extract_sheet_data(sheet_name)

    plfss_preprocessor = PLFSSPreProcessor(df)
    filtered_df = plfss_preprocessor.filter_amendements()
    shuffled_df = filtered_df.sample(frac=1).reset_index(drop=True)

    # Create a list to store the summaries and "Exposé amdt"
    data = []
    ollama_client = SummaryGeneratorOllamaClient()

    for i in range(nb_results):
        print(f"i : {i}")
        line = shuffled_df.iloc[i]
        exposé_des_motifs = line["Exposé amdt"]

        # prompt = ollama_client.build_prompt(exposé_des_motifs)
        # summary = ollama_client.generate_response(prompt)

        # experimental_prompt = ollama_client.build_prompt_experimental(exposé_des_motifs)
        # experimental_summary = ollama_client.generate_response(experimental_prompt)

        prompt3 = ollama_client.build_prompt_3(exposé_des_motifs)
        summary3 = ollama_client.generate_response(prompt3)

        # Append the data to the list
        data.append(
            {
                "Exposé amdt": exposé_des_motifs.replace('"', '""').replace("\n", " "),
                # TODO: this failed once because it thought line["Objet"] was a float
                "Objet (Expert)": line["Objet"].replace('"', '""').replace("\n", " "),
                "Objet 3": summary3.replace('"', '""').replace("\n", " "),
                # "Objet (LLaMa 3)": summary.replace('"', '""').replace("\n", " "),
                # "Objet (Exp LLaMa 3)": experimental_summary.replace('"', '""').replace(
                # "\n", " "
                # ),
            }
        )

    # Create a dataframe from the data
    df = pd.DataFrame(data)

    # Save the dataframe to a CSV file
    df.to_csv(object_samples_csv_path, index=False, encoding="utf-8-sig")
    print(f"Échantillon d'objets généré dans {object_samples_csv_path}")
