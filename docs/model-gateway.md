# Model Gateway

RHD uses a provider gateway instead of depending directly on one LLM.

Configured provider order defaults to:

`ollama,groq,openrouter,openai,deterministic`

Providers:

- Ollama: local/private option, configured with `OLLAMA_BASE_URL` and `OLLAMA_MODEL`.
- Groq: optional cloud provider, configured with `GROQ_API_KEY` and `GROQ_MODEL`.
- OpenRouter: optional cloud provider, configured with `OPENROUTER_API_KEY` and `OPENROUTER_MODEL`.
- OpenAI: optional cloud provider, configured with `OPENAI_API_KEY` and `OPENAI_MODEL`.
- Deterministic: always available fallback.

Private repository content defaults to local/deterministic processing unless `ALLOW_EXTERNAL_MODEL_FOR_PRIVATE_REPOS=true`.

The current implementation includes provider configuration, provider status, routing, telemetry rows, circuit-breaker state, and deterministic fallback. Network provider execution is intentionally conservative until keys and explicit validation are available.
