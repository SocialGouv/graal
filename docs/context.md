# GRAAL: Gestion et Répartition Automatisée des Amendements Législatifs

## Project Overview

GRAAL processes and analyzes legislative amendments to streamline government work. It groups similar amendments, assigns reviewers, generates summaries, and finds historical similarities using a feature-based architecture with parallel processing. The project includes both a CLI pipeline and a full-stack web application.

## Architecture

### Core System

- **Feature-based architecture**: Independent, modular features implementing `BaseFeature` interface
- **Parallel execution**: Features run concurrently using configurable thread pools
- **Two-phase processing**: Preprocessing features (filtering) → Parallel feature processing
- **Pipeline orchestrator**: Manages concurrent execution with error handling

### Web Application Stack

**Backend**: FastAPI with async processing, Pydantic validation, job registry for status tracking
**Frontend**: React 18 + TypeScript, DSFR design system ([react-dsfr](https://components.react-dsfr.codegouv.studio/?path=/docs/%F0%9F%87%AB%F0%9F%87%B7-introduction--page)), Zustand state management, React Query for API communication

### Project Structure

```txt
graal/
├── core/                    # Pipeline orchestration and feature interfaces
├── features/               # Modular feature implementations
├── api/                    # FastAPI web application
│   ├── routes/            # API endpoints
│   ├── services/          # Business logic
│   └── models/            # Pydantic models
├── allotment/             # Amendment grouping logic
├── attribution/           # Reviewer assignment
├── clustering/            # Similarity algorithms
├── summary/               # LLM summarization
├── similarities/          # Historical similarity search
└── utils/                 # Shared utilities
frontend/                  # React web application
```

## Data Flow

1. **Input Processing**: Load JSON/Excel → text normalization → configuration validation
2. **Column Management**: Clear columns for enabled features
3. **Phase 1**: Run preprocessing features (allotment) sequentially
4. **Phase 2**: Execute enabled features in parallel
5. **Result Merging**: Combine outputs using column ownership rules
6. **Output**: Export to Excel/CSV formats

## Key Features

| Feature               | Purpose                    | Key Algorithms                  | Output                    |
| --------------------- | -------------------------- | ------------------------------- | ------------------------- |
| **Allotment**         | Group identical amendments | TF-IDF + Damerau-Levenshtein    | Representative amendments |
| **Attribution**       | Assign to reviewers        | Keyword/table/legal matchers    | Reviewer assignments      |
| **Summary**           | Generate concise summaries | LLM with load balancing         | 8-20 word summaries       |
| **Similarity Search** | Find historical matches    | TF-IDF → Levenshtein refinement | Similar amendment data    |
| **Opinion**           | Handle government opinions | Rule-based processing           | Opinion classifications   |
| **Intra-lecture**     | Find session similarities  | Clustering algorithms           | Within-session matches    |

### Core Algorithms

- **TF-IDF**: Text vectorization for initial similarity clustering
- **Damerau-Levenshtein**: Precise string distance calculation
- **Cosine Similarity**: Vector similarity measurement
- **DBSCAN**: Density-based clustering

## Text Processing

### Amendment Preprocessing

- Acronym expansion using predefined mappings
- "Gage" phrase removal (standard legal text)
- Space/punctuation normalization
- Empty amendment handling with placeholder generation
- Mission filtering capabilities

### Feature-Specific Normalization

Each feature applies specialized text normalization optimized for its processing requirements.

## Web Application

### API Endpoints

- `POST /api/v1/process`: Upload and start processing
- `GET /api/v1/status/{job_id}`: Real-time job status
- `GET /api/v1/results/{job_id}/preview`: First 10 results
- `GET /api/v1/results/{job_id}/download`: Full CSV download

### Job Management

- **States**: `queued` → `running` → `completed`/`failed`/`timeout`
- **Progress tracking**: Percentage, status messages, timestamps
- **Error handling**: Validation, timeouts (60min), graceful failures
- **File management**: Temporary storage in `tmp/` directory

### Frontend Features

- Drag & drop JSON upload with validation
- Real-time progress tracking
- Results preview table
- CSV download functionality
- DSFR-compliant UI

## Configuration

YAML-based configuration controls:

- Enabled features and their parameters
- Similarity thresholds and algorithm settings
- Parallel processing (worker counts, timeouts)
- LLM provider settings with rate limiting
- Path validation and environment variable preprocessing

## LLM Integration

### Summary Generation

- Multiple LLM providers (Albert, Ollama, Scaleway)
- Load balancing with rate limiting
- Specific formatting rules (infinitive verbs, 8-20 words)
- Special handling for editorial amendments

### Attribution Matching

- **Keyword Matcher**: Text pattern matching
- **Credit Table Matcher**: Budget table analysis (PLF)
- **Legal Document Matcher**: Legal reference identification (PLFSS)
- **Redactional Matcher**: Editorial amendment handling

## Advanced Features

### Parallel Processing

- Configurable thread pools for feature execution
- Performance monitoring and logging
- Graceful error handling with continued processing
- Load balancing for external API calls

### Data Management

- **Value Preservation**: `no_value_overwrite` option
- **Column Ownership**: Prevents feature conflicts
- **Allotment Population**: Propagates results to filtered amendments
- **Concatenation Support**: For comment-like columns

## Testing & Development

### Test Structure

- **Unit Tests**: Feature-specific testing with pytest
- **Integration Tests**: End-to-end pipeline validation
- **API Tests**: REST endpoint testing

### Development Commands

```bash
# Backend
poetry run python start_web_server.py
poetry run uvicorn graal.api.main:app --reload

# Frontend
cd frontend && yarn dev
```

## Performance Considerations

- Async file I/O operations
- Non-blocking pipeline execution
- Efficient memory management with DataFrame strategies
- Configurable timeouts and retry mechanisms
- Rate limiting for external API calls
- Streaming file downloads for large results
