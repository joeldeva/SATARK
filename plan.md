# SATARK Fully Free Cloud Deployment Plan

## Target Architecture

- **Vercel Hobby** hosts the Vite frontend and `/api/*` proxy.
- **Render Free Web Service** hosts the Dockerized FastAPI backend.
- **Neon Free Postgres** stores application data and RAG chunks.
- **Upstash Redis Free** carries live events.
- **OpenRouter free model** powers assist-only generation.
- **Meta WhatsApp Cloud API** handles production WhatsApp messaging.

## Repo Changes Required For This Plan

- `render.yaml` defines the Render backend service.
- `apps/api/Dockerfile` runs Alembic then starts Uvicorn on `$PORT`.
- `rag_chunks` table stores retrieved source chunks in Postgres.
- RAG store supports `VECTOR_STORE=postgres`.
- Runtime readiness checks `database`, `redis`, `vector_store`, and `llm`.
- WhatsApp webhook supports Meta verification and outbound Graph API replies.
- `DEPLOY.md` documents exact setup steps and required secrets.

## Secrets The Repo Must Never Commit

```bash
DATABASE_URL
REDIS_URL
OPENROUTER_API_KEY
SECRET_KEY
WHATSAPP_VERIFY_TOKEN
WHATSAPP_ACCESS_TOKEN
WHATSAPP_PHONE_NUMBER_ID
BACKEND_URL
```

## Deployment Order

1. Create Neon Postgres and copy the pooled connection URL.
2. Create Upstash Redis and copy the `rediss://` URL.
3. Create OpenRouter key and choose a currently free model.
4. Create Render web service from this repo and set backend secrets.
5. Wait for Render `/health/ready` to return ready.
6. Set Vercel `BACKEND_URL` to the Render URL.
7. Deploy Vercel production.
8. Configure Meta WhatsApp webhook to the Render backend.
9. Run browser + WhatsApp smoke tests.

## Smoke Test Gate

- `/health/ready` is green.
- Login works.
- SDRD publish writes a survey.
- FOD assignment shows the survey.
- Collection/WhatsApp answers complete the survey.
- Suspicious answer creates Red trust score and `flag.created`.
- DPD and SCD read the persisted response from Postgres.
