# GRAAL: Gestion et Répartition Automatisée des Amendements Législatifs

## Project Overview

GRAAL processes and analyzes legislative amendments to streamline the work of government agents. It groups similar amendments, attributes them to appropriate reviewers, generates summaries, and finds historical similarities using a modern feature-based architecture with parallel processing capabilities.

## Core Architecture

### Project Structure

- `graal/`: Main package
  - `core/`: Core pipeline architecture and feature interfaces
    - `pipeline_orchestrator.py`: Manages parallel feature execution
    - `processing_pipeline.py`: Main pipeline implementation
    - `feature_interface.py`: Base interfaces for all features
    - `text_normalizers.py`: Feature-specific text normalization
  - `features/`: Modular feature implementations
    - `allotment_feature.py`: Amendment grouping (preprocessing)
    - `attribution_feature.py`: Reviewer assignment
    - `summary_feature.py`: LLM-based summarization
    - `similarity_search_feature.py`: Historical similarity search
    - `opinion_feature.py`: Opinion handling
    - `similarities_within_lecture_feature.py`: Intra-lecture similarities
  - `api/`: REST API layer (Clean Architecture)
    - `adapters/`: Database layer with models and repositories
    - `domain/`: Business logic with entities and use cases
    - `interface/`: REST routes, models, and services
  - `allotment/`: Amendment grouping logic
  - `attribution/`: Reviewer assignment logic
  - `clustering/`: Similarity algorithms implementation
  - `opinion/`: Opinion generation logic
  - `summary/`: LLM summarization implementation
  - `similarities/`: Similarity handling logic
  - `utils/`: Utilities and helpers

### Feature-Based Architecture

The system is built around independent, modular features that implement the `BaseFeature` interface:

- **Feature Independence**: Each feature works with immutable input data and has no cross-dependencies
- **Parallel Execution**: Features run concurrently using configurable thread pools
- **Two-Phase Processing**:
  1. Preprocessing features (like allotment) that can filter data
  2. Regular features that process the filtered dataset in parallel

### Data Flow

1. **Initial Preprocessing**: Load amendments from JSON/Excel files, apply basic text normalization
2. **Configuration Preprocessing**: Resolve environment variables, validate paths
3. **Column Clearing**: Clear columns that will be overwritten by enabled features
4. **Phase 1 - Preprocessing Features**: Run allotment and other filtering features sequentially
5. **Phase 2 - Parallel Feature Processing**: Execute enabled features concurrently
6. **Result Merging**: Combine feature outputs using column ownership rules
7. **Post-processing**: Handle special cases like allotment population and value preservation
8. **Output Generation**: Export results to Excel and CSV formats

## Key Features

### Amendment Preprocessing

- Acronym expansion using predefined mappings
- Removal of "gage" phrases (standard legal text)
- Normalization of spaces and punctuation
- Special handling for empty amendment bodies
- Mission filtering capabilities
- Placeholder body generation for empty amendments

### Allotment (Preprocessing Feature)

- Groups identical/near-identical amendments
- Uses TF-IDF (threshold ~0.4) for initial clustering
- Refines with Damerau-Levenshtein distance (threshold ~0.9999)
- Selects representative amendments and propagates information
- Runs as preprocessing feature to filter dataset before other features

### Attribution

- Assigns amendments to appropriate reviewers
- Uses specialized matchers:
  - Keyword Matcher: Finds keywords in text
  - Credit Table Matcher: Analyzes budget tables (PLF)
  - Legal Document Matcher: Identifies legal references (PLFSS)
  - Redactional Amendment Matcher: Handles editorial amendments
- Loads configuration from Excel files
- Runs in parallel with other features

### Similarity Search

- Finds similarities with historical amendments
- Two-phase approach:
  - TF-IDF vectorization for initial clustering
  - Damerau-Levenshtein for precise comparison
- Different thresholds for different amendment types
- Copies relevant information from similar amendments
- Configurable columns to copy from similar amendments

### Summary Generation

- Creates concise summaries using LLMs with load balancing
- Applies specific formatting rules:
  - Start with infinitive verb
  - Limited length (8-20 words)
  - Include essential information
- Uses multiple LLM clients with rate limiting
- Special handling for editorial amendments
- Supports multiple LLM providers (Albert, Ollama, Scaleway)

### Opinion Handling

- Manages government opinions on amendments
- Integrates with other features for comprehensive processing

### Similarities Within Lectures

- Identifies similar amendments within the same legislative session
- Complements historical similarity search

## Configuration

- YAML-based configuration controls enabled features
- Environment variable preprocessing and validation
- Configurable thresholds for similarity algorithms
- Parallel processing configuration (max workers, timeouts)
- Support for multiple LLM providers with rate limiting
- Path validation and preprocessing
- Feature-specific configuration sections

## Parallel Processing

- **PipelineOrchestrator**: Manages concurrent feature execution
- **Configurable Workers**: Adjustable thread pool size
- **Performance Monitoring**: Execution time tracking and logging
- **Error Handling**: Graceful failure handling with continued processing
- **Load Balancing**: Intelligent distribution of LLM requests

## Key Algorithms

- **TF-IDF**: Term frequency-inverse document frequency for text vectorization
- **Cosine Similarity**: Measures similarity between document vectors
- **Damerau-Levenshtein**: Calculates edit distance between strings
- **DBSCAN**: Density-based clustering for grouping similar amendments

## Advanced Features

### Value Preservation

- `no_value_overwrite` option to preserve original values
- Selective column preservation based on feature configuration

### Allotment Population

- Special handling to propagate results back to filtered amendments
- Maintains data integrity across the filtering process

### Column Management

- Automatic column clearing for enabled features
- Column ownership system prevents conflicts
- Concatenation support for comment-like columns

## Tests

- **Unit Tests**: Feature-specific testing with pytest
- **Integration Tests**: End-to-end pipeline testing
- **API Tests**: REST API endpoint testing
- Tests are run with pytest and organized by component

## Performance Optimizations

- Parallel feature execution reduces wall-clock time
- Efficient memory management with DataFrame copying strategies
- Rate limiting for external API calls
- Configurable timeouts and retry mechanisms
- Performance logging and monitoring
