# Amendements Intelligents

## Setup

### Install python dependencies

```bash
poetry install
```

### Prepare PLFSS data

Get an ALED file (here `data/aled.xlsm`) from the DSS 5A office.
Then extract PLFSS data from its sheets (here `PLFSS 2024`)

```bash
python amendements_intelligents/extract_plfss_excel_sheet.py --excel data/aled.xlsm --sheet "PLFSS 2024"
```

### Env variables

```bash
export DATA_FOLDER="data"
```

## Scripts

### Copy similar amendments

You must have PLFSS extracted into `data/PLFSS 2024.json` (Hardcoded for now, WIP)

```bash
python amendements_intelligents/populate_similarities.py
```

### Regroup similar amendements (allotment)

You must have PLFSS extracted into `data/PLFSS 2024.json` (Hardcoded for now, WIP)

```bash
python amendements_intelligents/populate_allotments.py
```

### Generate amendement summaries

\[WIP\]

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

Run the test suite with :

```bash
make test
```

### Integration tests

```bash
make integration_test
```
