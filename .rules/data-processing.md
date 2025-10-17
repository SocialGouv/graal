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

## Similarity Database Storage

**Storage Format**: Parquet files stored on S3 only
- **Rationale**: Efficient columnar format, cloud-native storage, better compression and performance
- **Location**: `{S3_SIMILARITY_DB_FOLDER}/project_name/*.parquet`
- **Loading**: Full database loaded into memory (required by TF-IDF algorithm)
- **Caching**: Databases cached in memory to avoid redundant S3 downloads

**Memory Considerations**:
- Similarity databases must be loaded completely into memory for TF-IDF vectorization
- Memory cache strategy reduces repeated S3 downloads of identical databases
- Use [`SimilarityDatabaseLoader`](graal/utils/similarity_db_loader.py) for async S3 loading

## Similarity Database Building

**Builder Responsibility**: [`SimilarityDatabaseBuilderService`](../graal/utils/similarity_db_builder_service.py) only builds the processed DataFrame:
- Amendment preprocessing (text normalization, acronym expansion)
- Deduplication via clustering (DBSCAN)
- Returns processed DataFrame ready for persistence

**Caller Responsibility**: File persistence and storage operations:
- Local file saving: Use `df.to_parquet(path, index=False)`
- S3 uploads: Caller handles S3 client and upload logic
- Any other storage operations

**Core Method**: `build_database()` returns the processed DataFrame:
```python
builder = get_similarity_db_builder()
df = await builder.build_database(
    project_names=["PLFSS"],
    drop_empty_columns=["Réponse"],
    similarity_threshold=0.99,
    eps=0.4
)
```
