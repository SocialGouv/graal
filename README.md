# Amendements Intelligents

## Setup

### Install python dependencies

```bash
make install
```

### Prepare PLFSS data

Get a PLFSS extract from Signale in JSON format

### Env variables

```bash
# Folder where your data (like the PLFSS JSON extract) can be found
export DATA_FOLDER="data"
```

## Scripts

### Copy similar amendments

You must have PLFSS extracted into `data/PLFSS_2024.json` (Hardcoded for now, WIP)

```bash
python amendements_intelligents/populate_similarities.py
```

### Regroup similar amendements (allotment)

You must have PLFSS extracted into `data/PLFSS_2024.json` (Hardcoded for now, WIP)

```bash
python amendements_intelligents/populate_allotments.py
```

### Generate amendement summaries

You must have PLFSS extracted into `data/PLFSS_2024.json` (Hardcoded for now, WIP)

```bash
python amendements_intelligents/summarize_plfss.py
```

## Tests

Run a single test file (here `tests/unit/test_text_utils.py`) with :

```bash
poetry run pytest tests/unit/test_text_utils.py
```

Run a single test (here `test_normalize_text`) within a specific test file (here `tests/unit/test_text_utils.py`) with :

```bash
poetry run pytest tests/unit/test_text_utils.py::test_normalize_text
```

### Unit tests

Run the unit test suite and coverage with :

```bash
make test
```

### Integration tests

Run the integration test suite with :

```bash
make integration_test
```

### Test coverage in VSCode

1. Install the [coverage-gutters](https://marketplace.visualstudio.com/items?itemName=ryanluker.vscode-coverage-gutters) extension
1. `Command Palette > Coverage Gutter: Display Coverage` (cmd + shift + 7) to show coverage in one file OR `Command Palette > Coverage Gutter: Watch` (cmd + shift + 8) to constantly show coverage and keep it updated on code changes

Some files are omitted by the coverage and you can find them in the pyproject.toml file under `tool.coverage.run.omit`
