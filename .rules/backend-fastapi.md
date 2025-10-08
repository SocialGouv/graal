# FastAPI Backend

## Purpose
API endpoints and web services for GRAAL amendment processing (`graal/api/`)

## Must Do
- Use `/api/v1/` prefix for versioning
- Define Pydantic models in `graal/api/models/` for validation
- Use async route handlers (`async def`) for non-blocking ops
- Job-based pattern for long-running tasks:
  - Create job with unique ID, return immediately
  - Process asynchronously in background
  - State transitions: `queued` → `running` → `completed`/`failed`/`timeout`
- Track progress with percentage, status, timestamps
- Set timeout limits (default: 60 minutes)
- Store temp files in `tmp/` with cleanup
- Separate business logic into `graal/api/services/`
- Return appropriate HTTP status codes

## Must Not Do
- Use synchronous blocking operations in route handlers
- Expose internal errors (return sanitized messages)
- Process large files synchronously
- Skip Pydantic validation
- Hardcode file paths

## Key Pattern
```python
@router.post("/process", response_model=JobResponse)
async def start_processing(file: UploadFile):
    job_id = await job_registry.create_job()
    # Start background processing
    return JobResponse(job_id=job_id, status="queued")

```
