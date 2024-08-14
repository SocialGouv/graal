import os
import time

from amendements_intelligents.summary.summary_processor import AmendmentSummaryProcessor
from amendements_intelligents.summary.vllm_client import LLMApiClient, VLLMApiClient
from amendements_intelligents.utils.plfss_pre_processor import PLFSSPreProcessor

MODEL_NAME = os.getenv("MODEL_NAME")
VLLM_ENDPOINT = os.getenv("VLLM_ENDPOINT")
USER = os.getenv("USER")
PASSWORD = os.getenv("PASSWORD")


def main():
    preprocessor = PLFSSPreProcessor()
    preprocessor.load_plfss_json("data/PLFSS_2024.json")
    preprocessor.remap_columns_in_json_amendments()
    amendments_df = preprocessor.prepare_work_amendments_df().copy()
    amendments_df["Objet 70B()"] = ""

    print(f"VLLM_ENDPOINT {VLLM_ENDPOINT}")
    vllm_client: LLMApiClient = VLLMApiClient(MODEL_NAME, VLLM_ENDPOINT, USER, PASSWORD)

    processor = AmendmentSummaryProcessor(amendments_df, vllm_client)

    start_time = time.time()

    print("Starting processing amendments...")
    start_index = 0
    stop_index = amendments_df.shape[0]
    processor.process_amendments(
        start_index=start_index,
        stop_index=stop_index,
    )

    for i in range(start_index, stop_index):
        print(
            f'amendments_df {i}, {amendments_df.loc[i, "Num amdt"]}, "Objet 70B()": {amendments_df.loc[i, "Objet 70B()"]}\n'
        )

    end_time = time.time()
    print(f"Time taken: {end_time - start_time} seconds")

    amendments_df.to_excel("data/amendments_with_summary.xlsx", index=False)


if __name__ == "__main__":
    main()
