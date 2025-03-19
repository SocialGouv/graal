# GRAAL - GESTION ET RÉPARTITION AUTOMATISÉE DES AMENDEMENTS LÉGISLATIFS

This project offers tools for processing and analyzing amendments, aiming to streamline and expedite the tasks of agents responsible for addressing these amendments.

## Project Structure

The project is organized into several main components:

- `graal/`: Main package containing the core functionality
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

export SCALEWAY_BASE_URL="https://<UUID_SCALEWAY>.ifr.fr-par.scaleway.com/v1"
export SCALEWAY_MODEL_NAME="meta/llama-3.3-70b-instruct:bf16"
export SCALEWAY_API_KEY="<API_KEY>"
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
python graal/full_pipeline.py --config=config/default.json
# OR
make run
```

To run the full pipeline without overwriting work already done in Signale:

```bash
python graal/full_pipeline.py --config=config/no_overwrite.json
# OR
make run-no-overwrite
```

### Config

Each feature mentioned above can be enabled or disabled through the configuration file. Some features also require specific text values to be set.

See [config/default.json](config/default.json) for the configuration we use most of the time.

Additionally, some parameters in the [graal/full_pipeline.py](graal/full_pipeline.py) script are currently hardcoded. You will need to modify the file directly (work in progress).

For instance, to enable or disable the use of Ollama, Albert API, Scaleway API, or the FakeLLMAPIClient (which outputs random Latin sentences), you can comment or uncomment the corresponding lines in this section of the code:

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

for _ in range(6):
    open_ai_api_client = OpenAIAPIClient(
        api_key=os.environ["SCALEWAY_API_KEY"],
        base_url=httpx.URL(os.environ["SCALEWAY_BASE_URL"]),
        model_name=os.getenv(
            "SCALEWAY_MODEL_NAME", "meta-llama/Meta-Llama-3.3-70B-Instruct"
        ),
    )
    llm_api_clients.append(open_ai_api_client)

llm_api_clients.append(FakeLLMAPIClient())
```

## Similarity Data Base

The system includes functionality to build a DB with old amendments for similarity search. This preprocessed data is used to find similarities between new and old amendments in the pipeline.

### Running the Script

You can run the script with specific projects or all projects:

```bash
# Process specific projects (e.g., PLFSS and PLACSS)
python graal/utils/build_similarity_db.py --projects PLFSS PLACSS

# Process all available projects
python graal/utils/build_similarity_db.py
```

### Adding New Projects

To add support for a new project type:

1. Create a new configuration file in `graal/utils/config/` (e.g., `my_project_config.py`) following this pattern:

```python
from pathlib import Path
from .base_config import ProjectConfig, InputFileConfig, create_timestamp, get_data_path

def get_my_project_config() -> ProjectConfig:
    """Get MyProject configuration."""

    json_configs: dict[Path, InputFileConfig] = {
        get_data_path("exports_lectures/MyProject/file1.json"): {
            "default_processing_timestamp": create_timestamp(2024, 1, 1),
            "origin_project": "MyProject 2024",
        },
    }

    excel_configs: dict[Path, InputFileConfig] = {
        get_data_path("exports_lectures/MyProject/file1.xlsx"): {
            "default_processing_timestamp": create_timestamp(2024, 1, 1),
            "origin_project": "MyProject 2024",
        },
    }

    return ProjectConfig(json_configs=json_configs, excel_configs=excel_configs)
```

1. Add your project to `ProjectConfigManager.AVAILABLE_PROJECTS` in `graal/utils/config/project_config_manager.py`:

```python
AVAILABLE_PROJECTS = {
    "PLFSS": get_plfss_config,
    "PLACSS": get_placss_config,
    # ... other projects ...
    "MY_PROJECT": get_my_project_config,  # Add your project here
}
```

```bash
python graal/utils/build_similarity_db.py --projects MY_PROJECT
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

## LLM hosted on remote machine

If we are not using Albert, we are probably running Ollama on an OVH machine at the moment.

To ssh on the machine : `ssh -i /Users/{you}/.ssh/{private_key} ubuntu@{IP_of_remote_machine}`

Then you can analyze what the machine is doing with :

```bash
cd /opt/ollama
tail -f init.log
docker compose logs
nvidia-smi
```

## Contributing

Please refer to the project's coding standards and best practices when contributing. Make sure to write tests for new functionality and update existing tests when necessary.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
