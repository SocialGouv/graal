# Technical Context

## Development Environment

### Core Technologies
- **Language**: Python
- **Package Manager**: Poetry
- **Build Tool**: Make
- **Container Platform**: Docker
- **Testing Framework**: pytest
- **Version Control**: Git

### External Services
1. **LLM Services**
   - Albert API (Etalab)
   - Ollama (Self-hosted)
   - FakeLLMAPIClient (Testing)

2. **Data Sources**
   - Signale (Amendment source)
   - Excel configuration files
   - JSON amendment data

## Setup Requirements

### Environment Variables
```bash
DATA_FOLDER="data"
ETALAB_API_KEY=<token>
ETALAB_BASE_URL="https://albert.api.etalab.gouv.fr/v1"
ETALAB_MODEL_NAME="meta-llama/Meta-Llama-3.1-70B-Instruct"
OLLAMA_ENDPOINT=https://<ip_address>.nip.io/api/generate
OLLAMA_USER=<user>
OLLAMA_PASSWORD=<password>
OLLAMA_MODEL_NAME="llama3.1:70b"
```

### Development Setup
1. Poetry environment activation
2. Python dependencies installation
3. Amendment data preparation
4. Excel configuration file setup

## Technical Constraints

### Data Processing
- Must preserve existing amendment values
- Handles empty amendment bodies
- Processes inadmissible amendments
- Maintains historical similarity data

### API Integration
- Rate limiting for LLM services
- Load balancing across multiple API clients
- Fallback mechanisms for API failures

### Configuration
- Project-specific configurations (PLFSS, PLACSS, etc.)
- Feature toggles via JSON config
- Non-overwrite options for existing work

### Testing Requirements
- Unit test coverage
- Integration test suite
- Test data in Excel format

## Development Workflow
1. Work in poetry shell
2. Run tests with coverage
3. Use pre-commit hooks
4. Follow project coding standards
5. Update tests for new features
6. Maintain documentation
