# Data Processing

## Must Do
- Use pandas DataFrames as primary data structure
- Apply text normalization before similarity algorithms
- Implement memory-efficient DataFrame operations
- Clear feature columns before processing when enabled

## Must Not Do
- Load entire datasets into memory unnecessarily
- Skip text normalization steps
- Mutate input DataFrames without copying

## Core Algorithms
- **TF-IDF**: Initial text vectorization for similarity clustering
- **Damerau-Levenshtein**: Precise string distance calculation (edit distance)
- **Cosine Similarity**: Vector similarity measurement for TF-IDF results
- **DBSCAN**: Density-based clustering for amendment grouping

## Text Normalization
- Acronym expansion using predefined mappings
- Remove "Gage" phrases (standard legal text)
- Normalize spaces and punctuation
- Handle empty amendments with placeholder generation
- Apply feature-specific normalization in processors

## DataFrame Patterns
- Column operations: Use `.copy()` to avoid mutations
- Batch processing: Process chunks for large datasets
- Column ownership: Each feature owns specific output columns
- Value preservation: Respect `no_value_overwrite` configuration
