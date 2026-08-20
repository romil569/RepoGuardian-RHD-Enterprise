# Production Architecture

Target architecture:

GitHub App
-> GitHub Webhooks
-> Event Gateway
-> Queue
-> Sync / Code / AI-ML Workers
-> Repository Intelligence Layer
-> SQL + Vector + Graph
-> Graph-RAG / Code-RAG
-> RHD Supervisor
-> Specialist Agents
-> ML Intelligence
-> Evidence Critic
-> Policy Engine
-> Human Control
-> Safe GitHub Actions

Implemented now:

- local development fallback
- model gateway abstraction
- local queue abstraction
- graph store abstraction with local backend
- webhook signature verification and event normalization
- code intelligence foundation
- ML model registry with honest status values
- production compose skeleton

Production dependencies remain optional for local demo:

- PostgreSQL + pgvector
- Redis
- GitHub App
- cloud or local model provider
- container platform
