# Storage & S3

## Must Do
- Use S3 for all configuration files and similarity databases in production
- Store configuration files as `.xlsx` format in S3
- Store similarity databases as Parquet files (`.parquet`) on S3
- Use `S3Service` for all S3 operations
- Validate S3 environment variables on initialization
- Use async operations for S3 database loading/uploading

## Must Not Do
- Hardcode S3 paths or credentials in code
- Use synchronous S3 operations for large file transfers
- Skip error handling for S3 operations
- Store sensitive data in S3 without proper access controls

## S3 Configuration

### Required Environment Variables
```bash
S3_BUCKET_ACCESS_KEY="<access_key>"
S3_BUCKET_SECRET_KEY="<secret_key>"
S3_BUCKET_ENDPOINT="https://s3.gra.io.cloud.ovh.net"
S3_BUCKET_NAME="graal-dev-app"
S3_BUCKET_REGION="gra"
S3_CONFIG_FOLDER="config_graal"              # Config files location
S3_SIMILARITY_DB_FOLDER="similarity_dbs"     # Similarity databases location
```

### Optional Timeouts/Retries
```bash
S3_CONNECT_TIMEOUT="10"    # Connection timeout in seconds
S3_READ_TIMEOUT="60"       # Read timeout in seconds
S3_MAX_RETRIES="3"         # Number of retry attempts
```

## Storage Locations

### Configuration Files
- **Format**: Excel files (`.xlsx`)
- **Location**: `s3://{S3_BUCKET_NAME}/{S3_CONFIG_FOLDER}/*.xlsx`
- **Purpose**: Store processing configuration for amendment pipelines
- **Access**: Loaded via web UI dropdown or API
- **Service**: [`S3Service`](../graal/utils/s3_service.py) - synchronous methods

**Example structure**:
```
s3://graal-dev-app/config_graal/
├── PLFSS_2024.xlsx
├── PLACSS_2023.xlsx
└── default_config.xlsx
```

### Similarity Databases
- **Format**: Parquet files (`.parquet`)
- **Location**: `s3://{S3_BUCKET_NAME}/{S3_SIMILARITY_DB_FOLDER}/{project}/*.parquet`
- **Purpose**: Preprocessed historical amendments for similarity search
- **Access**: Loaded on-demand with in-memory caching
- **Service**: [`S3Service`](../graal/utils/s3_service.py) - async methods

**Example structure**:
```
s3://graal-dev-app/similarity_dbs/
├── PLFSS/
│   ├── 2023.parquet
│   ├── 2024.parquet
│   └── combined.parquet
└── PLACSS/
    └── 2023.parquet
```

## Using S3Service

### Initialization
The S3Service is initialized as a singleton and validates all required environment variables:

```python
from graal.utils.s3_service import get_s3_service

s3_service = get_s3_service()  # Raises exception if S3 not configured
```

### Configuration Files (Synchronous)

**List available config files**:
```python
files = s3_service.list_available_config_files()
# Returns: ['PLFSS_2024.xlsx', 'PLACSS_2023.xlsx']
```

**Validate config file exists**:
```python
exists = s3_service.validate_config_file_exists("PLFSS_2024.xlsx")
# Returns: True/False
```

**Load config file**:
```python
df = s3_service.load_config_from_s3("PLFSS_2024.xlsx")
# Returns: pandas DataFrame with config data
```

### Similarity Databases (Async)

**List available databases**:
```python
databases = await s3_service.list_available_database_files("PLFSS")
# Returns: ['2023', '2024', 'combined'] (without .parquet extension)
```

**Load database**:
```python
df = await s3_service.load_database_parquet("PLFSS/2024")
# Returns: pandas DataFrame with preprocessed amendments
# Note: Handles .parquet extension automatically
```

**Upload database**:
```python
await s3_service.upload_database_parquet(df, "PLFSS/2024")
# Uploads df to s3://.../similarity_dbs/PLFSS/2024.parquet
```

## Similarity Database Caching

Use [`SimilarityDatabaseLoader`](../graal/utils/similarity_db_loader.py) for automatic caching:

```python
from graal.utils.similarity_db_loader import get_similarity_db_loader

loader = get_similarity_db_loader()

# Load from S3 with caching
df = await loader.load_from_s3("PLFSS/2024.parquet")

# Subsequent loads use cache
df_cached = await loader.load_from_s3("PLFSS/2024.parquet")  # Fast!

# Cache management
loader.clear_cache()                           # Clear all
loader.remove_from_cache("PLFSS/2024.parquet") # Remove specific
info = loader.get_cache_info()                 # Get statistics
```

**Why Caching?**
- Similarity databases must be fully loaded into memory for TF-IDF vectorization
- Multiple processing requests may use the same database
- Avoids redundant S3 downloads and parsing overhead

## Building & Uploading Databases

### Building Databases
Use [`SimilarityDatabaseBuilderService`](../graal/utils/similarity_db_builder_service.py):

```python
from graal.utils.similarity_db_builder_service import get_similarity_db_builder

builder = get_similarity_db_builder()

# Build processed DataFrame
df = await builder.build_database(
    project_names=["PLFSS"],
    drop_empty_columns=["Réponse"],
    similarity_threshold=0.99,
    eps=0.4
)

# DataFrame is ready but NOT persisted
# Caller is responsible for saving/uploading
```

### Uploading to S3

**Option 1: Using S3Service (in code)**:
```python
from graal.utils.s3_service import get_s3_service

s3_service = get_s3_service()
await s3_service.upload_database_parquet(df, "PLFSS/2024")
```

**Option 2: Save locally then use upload script**:
```python
# Save locally
df.to_parquet("data/preprocessed/PLFSS_2024.parquet", index=False)

# Upload using script
# poetry run python scripts/s3_upload.py \
#   data/preprocessed/PLFSS_2024.parquet \
#   --destination similarity_dbs/PLFSS/
```

### Upload Script
Use [`scripts/s3_upload.py`](../scripts/s3_upload.py) for manual uploads:

```bash
# Upload single file
poetry run python scripts/s3_upload.py \
  data/my_database.parquet \
  --destination similarity_dbs/PLFSS/

# Upload entire directory
poetry run python scripts/s3_upload.py \
  data/preprocessed/ \
  --destination similarity_dbs/

# Dry run (preview without uploading)
poetry run python scripts/s3_upload.py \
  data/preprocessed/ \
  --destination similarity_dbs/ \
  --dry-run
```

## Key Patterns

### Separation of Concerns
- **Builder**: Creates processed DataFrame (business logic)
- **Caller**: Handles persistence (storage logic)
- **S3Service**: Manages S3 operations (infrastructure)
- **Loader**: Provides caching layer (performance optimization)

### Async vs Sync
- **Sync operations**: Config file listing/loading (small files, infrequent)
- **Async operations**: Database loading/uploading (large files, frequent, potentially long-running)

### Data Sanitization
S3Service automatically sanitizes DataFrames before Parquet conversion:
- Converts object columns to Arrow-compatible types
- Decodes bytes/bytearray to UTF-8 strings
- Preserves NaN/None as nulls
- Uses pandas nullable string dtype for better compatibility
