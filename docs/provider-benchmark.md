# Provider Benchmark

Collected during activation on 2026-08-20.

No API keys are printed or stored in this document.

| Provider | Configured | Live Validated | Model | Latency | Schema Success | Tool Routing | Grounding | Notes |
|---|---|---|---|---:|---|---|---|---|
| Ollama | YES | YES | `qwen3:1.7b` | 15.6s gateway probe; 38.9s direct cold/simple probe | PARTIAL | YES | PARTIAL | Local `/api/generate` and FastAPI gateway validated; usable for proof, slow for demos |
| Groq | NO | NO | `llama-3.1-8b-instant` target | N/A | N/A | N/A | N/A | `GROQ_API_KEY` not present in process environment |
| OpenRouter | NO | NO | `openrouter/auto` target | N/A | N/A | N/A | N/A | `OPENROUTER_API_KEY` not present in process environment |
| OpenAI | NO | NO | `gpt-4o-mini` target | N/A | N/A | N/A | N/A | `OPENAI_API_KEY` not present in process environment |
| Deterministic | YES | YES | `template-router` | < 5 ms in unit tests | YES | YES | YES | Fallback remains active and tested |

## Tested Queries

The configured deterministic fallback, RHD tooling, and local Ollama provider path were validated with tests and route checks. Full RHD orchestration still uses the grounded deterministic intelligence path unless a workflow explicitly routes through the model gateway.

- What should I fix first?
- Why is repository health WATCH?
- Find duplicate issue clusters.
- Which issues need security review?
- What may have changed after v1.2.0?
- Give me a full repository review.
- Which PR appears highest risk?

## Local Model Notes

`qwen3:1.7b` is the active local default because it completed a bounded probe. `qwen3:8b` was pulled successfully but timed out on simple probes and is not treated as demo-ready on this machine.

## Secure Provider Setup

Add provider keys to local `.env` or a secure machine-level secret store. Do not paste API keys into chat.

For private repositories, cloud providers remain blocked unless `ALLOW_EXTERNAL_MODEL_FOR_PRIVATE_REPOS=true` is explicitly set.
