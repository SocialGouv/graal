# Backend Python

## Must Do
- Use Poetry for all dependency management
- Apply type hints to all functions and methods
- Use async/await for I/O operations (file reads, API calls)
- Organize code: core/ (orchestration), features/ (implementations), utils/ (shared)
- Import modules from graal.* namespace

## Must Not Do
- Install packages outside Poetry workflow
- Block on synchronous I/O in async functions
- Mix feature logic into core orchestration

## Key Patterns
- Features: Extend [`BaseFeature`](graal/core/feature_interface.py), implement `process()` method
- Async handlers: Use `async def`, await all I/O operations
- Pydantic models: Use for API request/response validation
- Module imports: `from graal.features import FeatureName`

## Type Hints
- Function signatures: `def process(data: pd.DataFrame) -> pd.DataFrame:`
- Async functions: `async def load_file(path: Path) -> dict[str, Any]:`
- Optional parameters: Use `Optional[Type]` or `Type | None`

## Error Handling
- Use structured exceptions with context
- Log errors with appropriate severity levels
- Allow pipeline to continue on feature failures
