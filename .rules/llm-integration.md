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

## Error Handling
- Handle API timeouts gracefully
- Log failed requests with context
- Continue processing on individual failures
