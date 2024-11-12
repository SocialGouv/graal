# Amendements Intelligents

This project provides tools for processing and analyzing amendments, particularly for the PLFSS (Projet de Loi de Financement de la Sécurité Sociale).

## Project Structure

The project is organized into several main components:

- `amendements_intelligents/`: Main package containing the core functionality
  - `allotment/`: Handles grouping of similar amendments
  - `attribution/`: Manages attribution of amendments
  - `clustering/`: Implements clustering and similarity finding algorithms
  - `opinion/`: Handles opinion-related functionality
  - `summary/`: Provides summarization capabilities
  - `utils/`: Contains utility functions and helpers
- `scripts/`: Contains utility scripts
- `tests/`: Contains unit and integration tests

## Setup

### Working with Poetry

We use poetry to handle dependencies and the python virtual environment. Make sure you are always working in the poetry shell when running scripts.

[Install poetry](https://python-poetry.org/docs/#installation)

Run the poetry shell to work in:

```bash
poetry shell
```

### Install Python Dependencies

```bash
make install
```

### Prepare PLFSS Data

Get some PLFSS extracts from Signale in JSON format and place them in your data folder.
This project comes with `PLFSS_2024.json` and `exports_lectures/PLFSS 2023`.

### Environment Variables

Set up the following environment variables:

```bash
# Folder where your data can be found
export DATA_FOLDER="data"

# Work with Albert API
export ETALAB_API_KEY=<albert_api_token>
export ETALAB_BASE_URL="https://albert.api.etalab.gouv.fr/v1"
export ETALAB_MODEL_NAME="meta-llama/Meta-Llama-3.1-70B-Instruct"

# Work with Ollama on OVH
export OLLAMA_ENDPOINT=https://<ip_address>.nip.io/api/generate
export OLLAMA_USER=<user>
export OLLAMA_PASSWORD=<password>
export OLLAMA_MODEL_NAME="llama3.1:70b"

```

## Pipeline

### Config

The configuration options for the pipeline can be set in a JSON file. Below are the available options and their descriptions:

- `allotments`: Enable allotments. (boolean)
- `already_processed_amdt_nums_path`: Path to a file containing amendment numbers that have already been processed and we want to ignore. (string)
- `attribution_interstitial_only`: Enable attribution only for interstitial amendments. (boolean)
- `attribution`: Enable attribution. (boolean)
- `default_opinion`: Enable default opinion. (boolean)
- `handle_inadmissible_amendments`: Enable handling inadmissible amendments. (boolean)
- `no_value_overwrite`: Disable overwriting values that are already present in the input amendments. (boolean)
- `placeholder_amdt_body`: Add placeholder text for empty amendment bodies. (boolean)
- `similarity_search`: Enable similarity search with older amendments. (boolean)
- `summary_generation`: Enable summary generation. (boolean)

See [config/default.json](config/default.json) for an example.

### Script

The full pipeline does all of the above at once.

To run the full pipeline:

```bash
python amendements_intelligents/full_pipeline.py --config=config/default.json
```

### Merge Amendment DataFrames

The [amendements_intelligents/utils/merge_amdt_df_into_another.py](amendements_intelligents/utils/merge_amdt_df_into_another.py) script enables us to seamlessly merge an existing CSV file of amendments that have already been processed in Signale with newly processed amendments from the pipeline. This script is particularly useful if any issues occur within the full pipeline, resulting in agents beginning work on amendments directly in Signale. Once the pipeline is repaired, we generate a new CSV for import into Signale. However, without this script, that import would overwrite prior work—a situation we aim to avoid.

To use this script, update file paths in the script and run the following command:

```bash
python amendements_intelligents/utils/merge_amdt_df_into_another.py
```

## Run through Docker

Build image:
```shell
docker build -t smart-amendments .
```

Run full pipepline:
```shell
docker run --env-file .env -v "$(pwd)/data":/app/data smart-amendments
```

## Tests

### Running Tests

To run a single test file:

```bash
poetry run pytest <path_to_test_file>
```

To run a single test within a specific test file:

```bash
poetry run pytest <path_to_test_file>::<test_name>
```

### Unit Tests

Run the unit test suite and coverage with:

```bash
make test
```

### Integration Tests

Run the integration test suite with:

```bash
make integration_test
```

### Test Coverage in VSCode

1. Install the [coverage-gutters](https://marketplace.visualstudio.com/items?itemName=ryanluker.vscode-coverage-gutters) extension
2. Use `Command Palette > Coverage Gutter: Display Coverage` (cmd + shift + 7) to show coverage in one file OR `Command Palette > Coverage Gutter: Watch` (cmd + shift + 8) to constantly show coverage and keep it updated on code changes

Some files are omitted by the coverage and you can find them in the pyproject.toml file under `tool.coverage.run.omit`

## Contributing

Please refer to the project's coding standards and best practices when contributing. Make sure to write tests for new functionality and update existing tests when necessary.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
