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
# Folder where your data (like the PLFSS JSON extract) can be found
export DATA_FOLDER="data"
export ETALAB_API_KEY="my_key"
export ETALAB_BASE_URL="https://albert.api.etalab.gouv.fr/v1"
export ETALAB_MODEL_NAME="meta-llama/Meta-Llama-3.1-70B-Instruct"
```

## Scripts

The project includes several scripts for different functionalities:

### Populate Similarities

This script calculates and populates the similarities between amendments.

```bash
python amendements_intelligents/populate_similarities.py
```

### Populate Allotments

This script handles the grouping of similar amendments into allotments.

```bash
python amendements_intelligents/populate_allotments.py
```

### Populate Attribution

This script manages the attribution of amendments to the appropriate agents based on the mappings file (ask the team to get a link to the excel mappings).

```bash
python amendements_intelligents/populate_attribution.py
```

### Populate Opinion

This script processes and populates opinion-related data for the amendments.

```bash
python amendements_intelligents/populate_opinion.py
```

### Populate Summaries

This script generates and populates summaries for the amendments.

```bash
python amendements_intelligents/populate_summaries.py
```

### Full Pipeline

The full pipeline does all of the above at once.

To run the full pipeline:

```bash
python amendements_intelligents/full_pipeline.py
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
