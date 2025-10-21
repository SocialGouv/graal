# Configuration

## Must Do
- Use YAML for all configuration files
- Store configs in `config/` directory
- Validate configuration on load with Pydantic models
- Preprocess environment variables in config values

## Must Not Do
- Hardcode configuration values in code
- Skip path validation for file/directory configs
- Ignore configuration validation errors

## Structure
- Feature parameters: Thresholds, enabled flags, column mappings
- Processing settings: Worker counts, timeouts, parallel execution
- LLM configuration: Provider settings, rate limits, model parameters
- Path configuration: Input/output directories, reference files
- Similarity database: S3 location, database file selection

## Validation
- Use Pydantic models for structure validation
- Validate paths exist before processing
- Check parameter ranges (e.g., thresholds 0-1)
- Expand environment variables: `${ENV_VAR}` syntax

## Key Patterns
- Load with [`ConfigPreprocessor`](graal/utils/config/config_preprocessor.py)
- Access via [`ProjectConfigManager`](graal/utils/config/project_config_manager.py)
- Feature configs: Nested under feature name keys

## Environment Variables

### S3 Configuration
For detailed S3 configuration and usage, see [storage-s3.md](storage-s3.md).

### Similarity Database Configuration
- **`S3_SIMILARITY_DB_FOLDER`**: S3 folder containing similarity databases as Parquet files
  - Default: `"similarity_dbs"`
  - Example: Databases stored at `s3://bucket/similarity_dbs/PLFSS/*.parquet`
  - Used by UI to list available databases and by loader to fetch files

### Feature Configuration Fields

**Similarity Search** (`similarity_search` key):
- `database_file`: (required) S3 path to Parquet similarity database file
  - Format: `"PLFSS/2024.parquet"` (relative to S3 similarity folder)
  - Only Parquet format on S3 is supported
  - Selected via UI dropdown when using web application
  - Must be present when similarity search feature is enabled
