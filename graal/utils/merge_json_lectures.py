import asyncio
import json
import logging
import logging.config
import os

from graal.utils.json_utils import load_json_from_file

logging.config.fileConfig("logging.conf")


async def main() -> None:
    DATA_FOLDER = os.getenv("DATA_FOLDER", "data")
    INPUT_FOLDER = f"{DATA_FOLDER}/exports_plfss/2023"
    OUTPUT_FILE = f"{DATA_FOLDER}/PLFSS_2023.json"

    # Iterate over each JSON file in the INPUT_FOLDER, open it as a JSON object, and merge its contents into a single JSON object
    output: dict[str, list] = {"amendements": []}
    filenames = await asyncio.to_thread(os.listdir, INPUT_FOLDER)
    for filename in filenames:
        if filename.endswith(".json"):
            file_path = f"{INPUT_FOLDER}/{filename}"
            data = await load_json_from_file(file_path)
            new_amendements = data["amendements"]
            output["amendements"].extend(new_amendements)

    # Dump merged amendments into a single file
    def _dump_output_sync() -> None:
        with open(OUTPUT_FILE, "w", encoding="utf-8-sig") as f:
            json.dump(output, f, ensure_ascii=False)

    await asyncio.to_thread(_dump_output_sync)
    logging.info(f"Merged lectures saved in {OUTPUT_FILE}")


if __name__ == "__main__":
    asyncio.run(main())
