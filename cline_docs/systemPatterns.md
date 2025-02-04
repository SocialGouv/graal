# System Patterns

## Architecture Overview
The project follows a modular architecture with clear separation of concerns:

### Core Components
1. **Allotment Module** (`graal/allotment/`)
   - Handles grouping of similar amendments
   - Implements allotment logic and handlers

2. **Attribution Module** (`graal/attribution/`)
   - Manages amendment attribution
   - Handles data loading and matching
   - Populates attribution data

3. **Clustering Module** (`graal/clustering/`)
   - Implements similarity finding algorithms
   - Handles inadmissible amendments
   - Manages cluster finding

4. **Opinion Module** (`graal/opinion/`)
   - Handles opinion-related functionality
   - Manages opinion generation and processing

5. **Summary Module** (`graal/summary/`)
   - Provides amendment summarization
   - Integrates with LLM clients
   - Manages load balancing for summary generation

6. **Utils Module** (`graal/utils/`)
   - Configuration management
   - Text processing utilities
   - Rate limiting
   - Data loading helpers

### Key Technical Patterns

1. **Configuration Management**
   - Project-specific configs (PLFSS, PLACSS, etc.)
   - Environment variable based configuration
   - JSON-based pipeline configuration

2. **Testing Strategy**
   - Comprehensive unit tests
   - Integration tests with test data
   - Coverage tracking and reporting

3. **Dependency Management**
   - Poetry for package management
   - Virtual environment isolation
   - Makefile for common operations

4. **Pipeline Architecture**
   - Modular pipeline stages
   - Feature toggles via configuration
   - Data preservation mechanisms

5. **LLM Integration**
   - Multiple LLM client support (Albert, Ollama)
   - Load balancing for API calls
   - Fallback to fake client for testing

6. **Docker Support**
   - Containerized deployment
   - Environment configuration via .env
   - Volume mounting for data

### Design Decisions
1. **Modularity**: Each component is self-contained with clear responsibilities
2. **Configurability**: Extensive use of configuration files for flexibility
3. **Testability**: Strong emphasis on automated testing
4. **Data Preservation**: Non-destructive processing of existing work
5. **Scalability**: Support for multiple LLM clients and load balancing
6. **Maintainability**: Clear project structure and documentation
