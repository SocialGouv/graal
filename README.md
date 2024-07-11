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
