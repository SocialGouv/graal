# Performance

## Must Do
- Use async file I/O for all file operations
- Configure thread pools for parallel feature execution
- Implement non-blocking pipeline execution
- Apply timeouts to all external API calls (default 60min for jobs)
- Rate limit external API requests per provider
- Stream large file downloads (CSV results)

## Must Not Do
- Block async event loop with synchronous I/O
- Skip timeout configuration on long-running operations
- Ignore rate limit errors from APIs

## Parallel Processing
- Configure worker counts per feature in YAML
- Use [`PipelineOrchestrator`](graal/core/pipeline_orchestrator.py) for concurrent execution
- Phase 1 (preprocessing) runs sequentially
- Phase 2 (features) runs in parallel with thread pools

## External APIs
- LLM calls: Load balance across providers with rate limiting
- Retry with exponential backoff on transient failures
- Log performance metrics (response times, throughput)

## Memory Management
- Process DataFrames in chunks for large datasets
- Clear temporary data after feature completion
- Use efficient pandas operations (vectorized, avoid iteration)
