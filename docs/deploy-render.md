# Render Deployment

Status: `READY_FOR_USER_AUTH`.

`render.yaml` defines a Render-compatible FastAPI web service. It does not create paid services by itself.

1. Create or connect a managed PostgreSQL database.
2. Enable pgvector if your provider requires manual extension setup.
3. Create a Render web service from this repository.
4. Set `DATABASE_URL`, `FRONTEND_URL`, `CORS_ORIGINS`, and any provider keys in Render environment settings.
5. Use health check path `/health`.

Start command:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

For Redis, set `QUEUE_BACKEND=redis` and `REDIS_URL`. Without Redis, use `QUEUE_BACKEND=postgres` after connecting managed PostgreSQL, or `local` for single-process demos only.
