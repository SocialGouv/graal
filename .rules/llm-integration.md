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
- Configure via YAML: endpoint, model, rate limit, timeout
- Use factory pattern: [`LLMFactory`](graal/summary/llm_factory.py)
- Client implementations: [`AlbertClient`](graal/summary/llm_clients.py), `OllamaClient`, `ScalewayClient`

## Rate limiting & throughput (common gotcha)

- **Where the RPM comes from**
  - CLI/YAML pipeline: `config["llm_clients"][provider]["rate_limit_per_minute"]` is read by
    `get_rate_limiting_config()` (`graal/summary/llm_factory.py`).
  - Web pipeline: `WebProcessingService._merge_frontend_config()` sets
    `config["llm_clients"][provider]["rate_limit_per_minute"]` from the selected DB `LlmConfig.rate_limit_per_minute`
    (DB + Pydantic default is **500**).
  - `SummaryGenerationLoadBalancer` enforces it with `TokenBucketRateLimiter` **per provider**.

- **If it “feels like 100/min” while configured at 500/min**
  - You may be **latency/concurrency limited**, not rate-limited.
  - In the web path, `nb_instances` is currently hard-coded to **8**, so effective throughput is roughly:
    `min(rate_limit_per_minute, nb_instances / avg_latency_seconds * 60)`.
    Example: 8 workers and ~5s/call ⇒ ~96 req/min.
  - Alternatively, the provider may enforce a lower **server-side** limit (look for HTTP 429 / RateLimit errors).

## Error Handling
- Handle API timeouts gracefully
- Log failed requests with context
- Continue processing on individual failures
