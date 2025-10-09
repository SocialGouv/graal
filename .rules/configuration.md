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

## Validation
- Use Pydantic models for structure validation
- Validate paths exist before processing
- Check parameter ranges (e.g., thresholds 0-1)
- Expand environment variables: `${ENV_VAR}` syntax

## Key Patterns
- Load with [`ConfigPreprocessor`](graal/utils/config/config_preprocessor.py)
- Access via [`ProjectConfigManager`](graal/utils/config/project_config_manager.py)
- Feature configs: Nested under feature name keys
