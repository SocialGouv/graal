# LLM Integration

## Must Do
- Support multiple providers: Albert, Ollama, Scaleway
- Implement load balancing across providers
- Apply rate limiting per provider
- Use infinitive verbs in summaries (French grammar)
- Generate summaries of 8-20 words

## Must Not Do
- Bypass rate limiting
- Generate summaries outside word count range
- Ignore provider-specific configuration

## Summary Rules
- Start with infinitive verb (e.g., "Modifier", "Supprimer", "Ajouter")
- Target 8-20 words (strict requirement)
- Use clear, concise language
- Special handling for editorial amendments (amendments rédactionnels)

## Load Balancing
- Use [`SummaryGenerationLoadBalancer`](graal/summary/summary_generation_load_balancer.py)
- Distribute requests across available providers
- Respect per-provider rate limits
- Implement retry logic with exponential backoff

## Provider Management
- Configure via DB `LlmConfig` (provider, model, base_url/api_key, rate limit, concurrency)
- Use factory helpers in [`graal/summary/llm_factory.py`](../graal/summary/llm_factory.py)
- Client implementations: [`OpenAIAPIClient`](../graal/summary/llm_clients.py), `FakeLLMAPIClient`

## Rate limiting & throughput (common gotcha)

- **Where the RPM comes from**
  - Web/DB pipeline: selected `summary_generation.llm_config_id` is resolved to a DB `LlmConfig`.
  - RPM comes from `LlmConfig.rate_limit_per_minute` (DB + Pydantic default is **500**) and is enforced by
    `SummaryGenerationLoadBalancer` with `TokenBucketRateLimiter`.
  - `SummaryGenerationLoadBalancer` enforces it with `TokenBucketRateLimiter` **per provider**.

- **If it “feels like 100/min” while configured at 500/min**
  - You may be **latency/concurrency limited**, not rate-limited.
  - In the web path, concurrency comes from the selected DB `LlmConfig.max_concurrent_requests` (default **6**),
    so effective throughput is roughly:
    `min(rate_limit_per_minute, max_concurrent_requests / avg_latency_seconds * 60)`.
    Example: 6 workers and ~5s/call ⇒ ~72 req/min.
  - Alternatively, the provider may enforce a lower **server-side** limit (look for HTTP 429 / RateLimit errors).

## Error Handling
- Handle API timeouts gracefully
- Log failed requests with context
- Continue processing on individual failures
