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
eval $(poetry env activate)
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
python graal/full_pipeline.py --config=config/default.yml
# OR
make run
```

To run the full pipeline without overwriting work already done in Signale:

```bash
python graal/full_pipeline.py --config=config/no_overwrite.yml
# OR
make run-no-overwrite
```

### Config

Each feature mentioned above can be enabled or disabled through the configuration file.

The system uses YAML configuration format:

```bash
python graal/full_pipeline.py --config=config/default.yml
```

See [config/default.yml](config/default.yml) for the configuration we use most of the time.

**Example YAML Configuration**:

```yaml
# GRAAL Configuration File
# This file contains all configuration parameters for the GRAAL amendment processing system

# Threshold for TF-IDF similarity calculations
tf_idf_threshold: 0.4

# Allotment configuration - groups amendments by similarity
allotments:
  enabled: true
  column: "Corps amdt"  # Column used for similarity comparison
  similarity_threshold: 0.9999  # Threshold above which amendments are considered similar
```

#### LLM Client Configuration

You can configure LLM clients using the `llm_clients` section in your configuration file:

```yaml
# LLM client configuration
llm_clients:
  scaleway:
    nb_instances: 6
    timeout: 30
  albert:
    nb_instances: 3
    rate_limiting: 100
```

Each client type can have the following parameters:

- `nb_instances`: Number of client instances to create (required)
- `timeout`: Request timeout in seconds (optional, defaults to 30)
- `rate_limiting`: Rate limit in requests per minute (optional)

Supported client types:

- `scaleway`: Scaleway API
- `albert`: Albert API from Etalab
- `ollama`: Ollama API
- `fake`: Fake client for testing
- `vllm`: vLLM API

#### Similarity Search Configuration

You can configure the similarity search feature using the `similarity_search` section in your configuration file:

```yaml
# Similarity search configuration
similarity_search:
  enabled: true
  columns_to_copy:
    Réponse:
      enabled: true
    Sort:
      enabled: true
      condition: "irrecevable"
    Objet:
      enabled: false
```

Parameters:

- `enabled`: Enable or disable the similarity search feature
- `columns_to_copy`: Specify which columns should be copied from similar amendments
  - Each column can have the following settings:
    - `enabled`: Whether to copy this column from similar amendments
    - `condition`: Optional condition that must be met to copy the column (e.g., only copy "Sort" when it contains "irrecevable")

#### Summary Generation Configuration

You can configure the summary generation feature using the `summary_generation` section in your configuration file:

```yaml
# Summary generation configuration
summary_generation:
  enabled: true
  should_overwrite: false
```

Parameters:

- `enabled`: Enable or disable the summary generation feature
- `should_overwrite`: Controls how existing summaries are handled:
  - When `true`: All summaries are regenerated, including existing ones
  - When `false`: Only empty summaries are generated, existing summaries are preserved

This is particularly useful when you want to preserve manually edited summaries or when you want to regenerate all summaries with an updated prompt or model.

## Web API

GRAAL now includes a REST API that provides web-based access to the amendment processing pipeline. The API allows users to upload JSON files, process them through the GRAAL pipeline, and retrieve results via HTTP endpoints.

### Getting Started

Start the web server using the provided startup script:

```bash
# Using the startup script
python start_web_server.py

# Or directly with uvicorn
uvicorn graal.api.main:app --host localhost --port 8000 --reload
```

The API will be available at `http://localhost:8000` with automatic API documentation at `http://localhost:8000/docs`.

### Usage Example

Here's a complete example of using the API with curl:

```bash
# 1. Upload and start processing
curl -X POST "http://localhost:8000/api/v1/process" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@amendments.json"

# Response: {"job_id": "abc123", "status": "queued", "message": "Processing job started"}

# 2. Check processing status
curl "http://localhost:8000/api/v1/status/abc123"

# 3. Get results preview (when completed)
curl "http://localhost:8000/api/v1/results/abc123/preview"

# 4. Download full results
curl "http://localhost:8000/api/v1/results/abc123/download" -o results.csv
```

### Configuration

The web API uses the same configuration system as the command-line pipeline:

- **Configuration File**: Uses `config/default.yml` by default
- **File Size Limit**: 50MB maximum for uploaded files
- **Processing Timeout**: 60 minutes maximum per job
- **Temporary Files**: Stored in `tmp/` directory
- **CORS**: Configured for development with Vite dev server (`http://localhost:5173`)

### Development

For development, the API includes:

- **Auto-reload**: Enabled when running with `--reload` flag
- **CORS Middleware**: Allows cross-origin requests from frontend
- **Logging**: Comprehensive logging for debugging
- **Error Handling**: Graceful error handling with appropriate HTTP status codes

## Web Application Frontend

GRAAL now includes a modern web application frontend that provides a user-friendly interface for uploading and processing amendments through the web browser. The frontend is built with React, TypeScript, and the French Government Design System (DSFR).

### Technology Stack

- **React 18** with TypeScript for type safety
- **Vite** for fast development and building
- **Yarn Berry (v4+)** for modern package management
- **DSFR (Système de Design de l'État)** for French government compliant UI
- **API Integration** with the FastAPI backend

### Getting Started

#### Prerequisites

Make sure you have Node.js (v18+) and Yarn installed on your system.

#### Installation and Setup

1. **Navigate to the frontend directory:**

   ```bash
   cd frontend
   ```

2. **Install dependencies:**

   ```bash
   yarn install
   ```

3. **Start the development server:**

   ```bash
   yarn dev
   ```

   The frontend will be available at `http://localhost:5173/`

#### Running the Full Stack

To use the complete web application, you need both the backend API and frontend running:

1. **Start the backend API** (in the project root):

   ```bash
   python start_web_server.py
   ```

   Backend will run on `http://localhost:8000`

2. **Start the frontend** (in a separate terminal):

   ```bash
   cd frontend
   yarn dev
   ```

   Frontend will run on `http://localhost:5173/`

3. **Open your browser** and navigate to `http://localhost:5173/`

### Features

The web application provides:

- **File Upload Interface**: Drag & drop or browse to upload JSON amendment files (max 50MB)
- **Processing Progress**: Real-time progress tracking with status updates
- **Results Preview**: View the first 10 processed amendments in a table
- **CSV Download**: Download the complete processed results
- **DSFR Compliance**: French government design system for accessibility and consistency
- **Responsive Design**: Works on desktop and mobile devices

### Usage

1. **Upload Amendments**: Use the file upload interface to select a JSON file containing amendments
2. **Monitor Progress**: Watch the processing progress with real-time status updates
3. **Review Results**: Preview the processed amendments in the results table
4. **Download Results**: Download the complete CSV file with all processed amendments

### Development

#### Available Scripts

- `yarn dev` - Start development server with hot reload
- `yarn build` - Build for production
- `yarn preview` - Preview production build locally
- `yarn lint` - Run ESLint for code quality

#### API Integration

The frontend automatically proxies API requests to the backend server running on `http://localhost:8000`. This is configured in `vite.config.ts` and allows seamless communication between frontend and backend during development.

### Deployment

For production deployment, build the frontend and serve the static files:

```bash
cd frontend
yarn build
```

The built files will be in the `frontend/dist/` directory and can be served by any static file server.

## Similarity Data Base

The system includes functionality to build a DB with old amendments for similarity search. This preprocessed data is used to find similarities between new and old amendments in the pipeline.

### Running the Script

You can run the script with specific projects or all projects:

```bash
# Process specific projects (e.g., PLFSS and PLACSS)
python graal/utils/build_similarity_db.py --projects PLFSS PLACSS

# Process all available projects
python graal/utils/build_similarity_db.py

# Specify columns to drop empty rows from (default is ["Réponse"])
python graal/utils/build_similarity_db.py --drop-empty-columns Réponse "Objet amdt"

# Specify output file path
python graal/utils/build_similarity_db.py --output data/preprocessed/custom_db.pkl
```

The script supports the following command-line options:

- `--projects`: List of projects to include (e.g., PLFSS PLACSS). If not specified, includes all projects.
- `--output`: Output pickle file path (default: data/preprocessed/pre_processed_old_amdts.pkl)
- `--drop-empty-columns`: List of columns to drop rows from if they are empty (default: ['Réponse'])

### Adding New Projects

To add support for a new project type:

1. Add the project configuration to the YAML file at `config/db_amendments/projects.yml` following this pattern:

```yaml
projects:
  # Existing projects...

  MY_PROJECT:  # Your project name in uppercase
    json_configs:
      - path: "exports_lectures/MyProject_2024/file1.json"
        default_processing_timestamp:
          year: 2024
          month: 1
          day: 1
        origin_project: "MyProject 2024"
    excel_configs:
      - path: "exports_lectures/MyProject_2024/file2.xlsx"
        default_processing_timestamp:
          year: 2024
          month: 1
          day: 1
        origin_project: "MyProject 2024"
```

That's it! No need to modify any Python code. The system will automatically load your project configuration from the YAML file.

You can then run the script with your new project:

```bash
python graal/utils/build_similarity_db.py --projects MY_PROJECT --output data/preprocessed/my_project_db.pkl
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
