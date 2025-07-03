# GRAAL: Gestion et Répartition Automatisée des Amendements Législatifs

## Project Overview

GRAAL processes and analyzes legislative amendments to streamline the work of government agents. It groups similar amendments, attributes them to appropriate reviewers, generates summaries, and finds historical similarities.

## Core Architecture

### Project Structure

- `graal/`: Main package
  - `allotment/`: Groups similar amendments
  - `attribution/`: Assigns amendments to reviewers
  - `clustering/`: Implements similarity algorithms
  - `opinion/`: Handles opinion generation
  - `summary/`: Provides summarization capabilities
  - `utils/`: Contains utilities and helpers

### Data Flow

1. Amendments are loaded from JSON/Excel files
2. Text preprocessing normalizes content
3. Pipeline applies enabled features in sequence
4. Results are exported back to JSON

## Key Features

### Amendment Preprocessing

- Acronym expansion using predefined mappings
- Removal of "gage" phrases (standard legal text)
- Normalization of spaces and punctuation
- Special handling for empty amendment bodies

### Allotment

- Groups identical/near-identical amendments
- Uses TF-IDF (threshold ~0.4) for initial clustering
- Refines with Damerau-Levenshtein distance (threshold ~0.9999)
- Selects representative amendments and propagates information

### Attribution

- Assigns amendments to appropriate reviewers
- Uses specialized matchers:
  - Keyword Matcher: Finds keywords in text
  - Credit Table Matcher: Analyzes budget tables (PLF)
  - Legal Document Matcher: Identifies legal references (PLFSS)
- Loads configuration from Excel files

### Similarity Search

- Finds similarities with historical amendments
- Two-phase approach:
  - TF-IDF vectorization for initial clustering
  - Damerau-Levenshtein for precise comparison
- Different thresholds for different amendment types
- Copies relevant information from similar amendments

### Summary Generation

- Creates concise summaries using LLMs
- Applies specific formatting rules:
  - Start with infinitive verb
  - Limited length (8-20 words)
  - Include essential information
- Uses load balancing across multiple LLM clients
- Special handling for editorial amendments

## Configuration

- YAML-based configuration controls enabled features
- Environment variables for LLM API connections
- Configurable thresholds for similarity algorithms
- Support for multiple LLM providers (Albert, Ollama, Scaleway)

## Key Algorithms

- TF-IDF: Term frequency-inverse document frequency for text vectorization
- Cosine similarity: Measures similarity between document vectors
- Damerau-Levenshtein: Calculates edit distance between strings
- DBSCAN: Density-based clustering for grouping similar amendments
