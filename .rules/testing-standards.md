# Testing Standards

## Must Do
- Use pytest for all tests
- Organize: tests/unit/ (feature-specific), tests/integration/ (end-to-end)
- Write unit tests for each feature implementation
- Include integration tests for full pipeline flows

## Must Not Do
- Skip test coverage for new features
- Mix unit and integration test concerns
- Commit failing tests

## Test Organization
- Unit tests: `tests/unit/<module>/<file>_test.py`
- Integration tests: `tests/integration/<feature>_test.py`
- Test data: `tests/integration/test_data/`

## Unit Tests
- Test individual feature methods in isolation
- Mock external dependencies (LLM calls, file I/O)
- Focus on business logic correctness
- Use pytest fixtures for test data

## Integration Tests
- Test complete feature pipelines
- Use real test data files
- Verify end-to-end data transformations
- Test API endpoints with realistic payloads
