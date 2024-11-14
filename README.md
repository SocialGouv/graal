# GRAAL - GESTION ET RÉPARTITION AUTOMATISÉE DES AMENDEMENTS LÉGISLATIFS

This project offers tools for processing and analyzing amendments, aiming to streamline and expedite the tasks of agents responsible for addressing these amendments.

## Project Structure

The project is organized into several main components:

- `amendements_intelligents/`: Main package containing the core functionality
  - `allotment/`: Handles grouping of similar amendments
  - `attribution/`: Manages attribution of amendments
  - `clustering/`: Implements clustering and similarity finding algorithms
  - `opinion/`: Handles opinion-related functionality
  - `summary/`: Provides summarization capabilities
  - `utils/`: Contains utility functions and helpers
- `data/`: Contains some example data to run the pipeline on.
- `scripts/`: Contains utility scripts
- `tests/`: Contains unit and integration tests
- `config/`: Contains preset configuration files for the pipeline

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

### Prepare amendments Data

Extracts amendments from Signale in JSON format and place them in your data folder.
This project comes with `PLFSS_2024.json` and `exports_lectures/PLFSS 2023`.

### Download the Excel configuration file

If you are part of the "Ministères sociaux", you should be able to access the [configuration file](https://msociauxfr.sharepoint.com/:x:/t/FabNum/EUAB4dL6TVNFs4bJsGvhS6cBRm5rmM6nXEbAznY4dNZIiA?e=OnPXEO) on your own, which you can copy and adapt to your use case.

Otherwise, get in touch with the "Fabrique du numérique des ministères sociaux".

### Environment Variables

Set up the following environment variables:

```bash
# Folder where your data can be found
export DATA_FOLDER="data"

# If your work with Albert API
export ETALAB_API_KEY=<albert_api_token>
export ETALAB_BASE_URL="https://albert.api.etalab.gouv.fr/v1"
export ETALAB_MODEL_NAME="meta-llama/Meta-Llama-3.1-70B-Instruct"

# If you work with Ollama on OVH
export OLLAMA_ENDPOINT=https://<ip_address>.nip.io/api/generate
export OLLAMA_USER=<user>
export OLLAMA_PASSWORD=<password>
export OLLAMA_MODEL_NAME="llama3.1:70b"
```

**NB:** You can still test GRAAL without using Albert or Ollama by using the FakeLLMAPIClient. See [pipeline](#pipeline)

## Pipeline

### Pipeline Overview

The pipeline is designed to process and analyze amendments efficiently. It consists of several stages, each responsible for a specific task. Below is an overview of the main features and their functionalities:

- **Allotments**: Groups similar amendments together to streamline processing.
- **Already Processed Amendments**: Skips amendments that have already been processed, using a specified file containing their numbers.
- **Attribution**: Assigns amendments to the appropriate agents, with an option to focus only on interstitial amendments. This attribution is configured through an excel configuration file.
- **Default Opinion**: Automatically generates a default opinion for amendments.
- **Handling Inadmissible Amendments**: Identifies and processes inadmissible amendments.
- **Preserve Existing Values**: Ensures that existing values in the input amendments are not overwritten. This is particularly useful when running GRAAL after some agents have already started working on the amendments.
- **Placeholder Amendment Body**: Adds placeholder text for amendments that have empty bodies.
- **Similarity Search**: Finds and links amendments that are similar to older ones, aiding in consistency and historical context.
- **Summary Generation**: Creates summaries for amendments to provide a quick overview.

These features work together to ensure that amendments are processed accurately and efficiently, reducing the workload on agents and improving the overall workflow.

### Script

To run the full pipeline:

```bash
python amendements_intelligents/full_pipeline.py --config=config/default.json
```

### Config

Each feature mentioned above can be enabled or disabled through the configuration file. Some features also require specific text values to be set.

See [config/default.json](config/default.json) for the configuration we use most of the time.

Additionally, some parameters in the [amendements_intelligents/full_pipeline.py](amendements_intelligents/full_pipeline.py) script are currently hardcoded. You will need to modify the file directly (work in progress).

For instance, to enable or disable the use of Ollama, Albert API, or the FakeLLMAPIClient (which outputs random Latin sentences), you can comment or uncomment the corresponding lines in this section of the code:

```python
llm_api_clients = []
for _ in range(10):
    ollama_api_client = OllamaAPIClient(
        endpoint=os.getenv("OLLAMA_ENDPOINT"),
        model_name=os.getenv("OLLAMA_MODEL_NAME"),
        user=os.getenv("OLLAMA_USER"),
        password=os.getenv("OLLAMA_PASSWORD"),
    )
    llm_api_clients.append(ollama_api_client)

for _ in range(6):
    albert_api_client = AlbertAPIClient(
        base_url=os.getenv(
            "ETALAB_BASE_URL", "https://albert.api.etalab.gouv.fr/v1"
        ),
        api_key=os.getenv("ETALAB_API_KEY"),
        model_name=os.getenv(
            "ETALAB_MODEL_NAME", "meta-llama/Meta-Llama-3.1-70B-Instruct"
        ),
    )
    llm_api_clients.append(albert_api_client)

llm_api_clients.append(FakeLLMAPIClient())
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
