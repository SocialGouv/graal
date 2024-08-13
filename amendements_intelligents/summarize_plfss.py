import concurrent.futures
import os
import time

from amendements_intelligents.summary.summary_prompt_builder import SummaryPromptBuilder
from amendements_intelligents.summary.vllm_client import VLLMClient
from amendements_intelligents.utils.plfss_pre_processor import PLFSSPreProcessor

MODEL_NAME = os.getenv("MODEL_NAME")
HOST = os.getenv("HOST")
USER = os.getenv("USER")
PASSWORD = os.getenv("PASSWORD")

preprocessor = PLFSSPreProcessor()
preprocessor.load_plfss_json("data/PLFSS_2024.json")
preprocessor.remap_columns_in_json_amendments()
amendments_df = preprocessor.prepare_work_amendments_df().copy()
amendments_df["Objet 70B()"] = ""

start_time = time.time()
# url = f"http://{HOST}:8000/v1/completions"
url = f"https://{HOST}/v1/completions"

headers = {"Content-Type": "application/json"}
auth = (USER, PASSWORD)

prompt_builder = SummaryPromptBuilder()
vllm_client = VLLMClient(MODEL_NAME, HOST, USER, PASSWORD)


def submit_and_track_futures(
    executor, amendments_df, start_index=0, stop_index=25, max_concurrent=10
):
    print(f"Stopping at index {stop_index}")
    futures_to_index = {}

    # Submit initial batch of tasks
    for i in range(max_concurrent):
        if start_index + i >= amendments_df.shape[0]:
            break
        index = start_index + i
        row = amendments_df.iloc[index]
        if row["Exposé amdt"].strip() != "":
            prompt = prompt_builder.build_prompt(
                explanatory_statement=row["Exposé amdt"], body=row["Corps amdt"]
            )
            future = executor.submit(vllm_client.generate_summary, prompt)
            futures_to_index[future] = index
            print(f"Submitted task for index {index}")

    # Process completed futures and submit new tasks as old ones complete
    next_index = start_index + max_concurrent
    while futures_to_index or (
        next_index < amendments_df.shape[0] and next_index < stop_index
    ):
        if futures_to_index:
            completed_future = next(concurrent.futures.as_completed(futures_to_index))
            summary = completed_future.result()
            idx = futures_to_index.pop(completed_future)
            amendments_df.loc[idx, "Objet 70B()"] = summary
            print(f"COMPLETED: {idx}")

        # Submit a new task if there are more rows to process
        row = amendments_df.iloc[next_index]
        if row["Exposé amdt"].strip() != "":
            prompt = prompt_builder.build_prompt(
                explanatory_statement=row["Exposé amdt"], body=row["Corps amdt"]
            )
            future = executor.submit(vllm_client.generate_summary, prompt)
            futures_to_index[future] = next_index
            print(f"Submitted task for index {next_index}")
        next_index += 1


max_concurrent = 10
start_index = 1580
# Main execution with thread pool
with concurrent.futures.ThreadPoolExecutor(max_workers=max_concurrent) as executor:
    submit_and_track_futures(
        executor,
        amendments_df,
        start_index=start_index,
        stop_index=amendments_df.shape[0],
        max_concurrent=max_concurrent,
    )

for i in range(start_index, start_index + 25):
    print(
        f'amendments_df {i}, {amendments_df.loc[i, "Num amdt"]}, "Objet 70B()": {amendments_df.loc[i, "Objet 70B()"]}\n'
    )

executor.shutdown(wait=True)

print(f'amendments_df.loc[0, "Objet 70B()"] {amendments_df.loc[0, "Objet 70B()"]}')
end_time = time.time()
print(f"Time taken: {end_time - start_time} seconds")

amendments_df.to_excel("data/amendments_with_summary.xlsx", index=False)
