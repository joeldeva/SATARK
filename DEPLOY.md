# SATARK Fully Free Cloud Deployment

This deployment uses free tiers only where possible:

| Layer | Platform | Runs |
| --- | --- | --- |
| Frontend/proxy | Vercel Hobby | React/Vite static app + `/api/*` proxy |
| Backend | Render Free Web Service | FastAPI Docker service |
| Database | Neon Free Postgres | Surveys, responses, paradata, trust, audit, RAG chunks |
| Events | Upstash Redis Free | `response.scored`, `flag.created`, `trust.updated`, sandbox live feed |
| Assist LLM | OpenRouter free model | Survey draft assist only, never verdict authority |
| WhatsApp | Meta WhatsApp Cloud API | Production respondent channel |

Baileys remains useful for local WhatsApp testing, but it is not the cloud
production bridge. Production WhatsApp uses Meta webhook callbacks and Graph API
replies.

## 1. Backend: Render

Create a Render Web Service from this repository using `render.yaml`.

Required Render environment variables:

```bash
DATABASE_URL=<Neon pooled PostgreSQL URL, SQLAlchemy psycopg format>
REDIS_URL=<Upstash rediss URL>
OPENROUTER_API_KEY=<OpenRouter key>
WHATSAPP_VERIFY_TOKEN=<Meta webhook verify token>
WHATSAPP_ACCESS_TOKEN=<Meta WhatsApp Cloud API token>
WHATSAPP_PHONE_NUMBER_ID=<Meta phone number id>
```

`render.yaml` sets the non-secret values:

```bash
LLM_PROVIDER=openrouter
OPENROUTER_MODEL=nex-agi/nex-n2-pro:free
LLM_REQUIRED=false
VECTOR_STORE=postgres
WHATSAPP_PROVIDER=meta
```

Render starts the API with:

```bash
python -m alembic upgrade head
python -m uvicorn main:app --host 0.0.0.0 --port $PORT
```

Health checks:

```bash
GET https://<render-service>.onrender.com/health
GET https://<render-service>.onrender.com/health/ready
```

## 2. Database: Neon

Create one Neon Postgres project. Use the pooled connection string in Render as
`DATABASE_URL`.

The backend stores:

- `surveys`, `assignments`, `enumerators`, `households`
- `responses`, `paradata`, `validation_results`, `trust_scores`
- `generation_logs`, `audit_logs`
- `rag_chunks` for cloud RAG/provenance without Chroma

Use the SQLAlchemy psycopg URL shape:

```bash
postgresql+psycopg://USER:PASSWORD@HOST/DB?sslmode=require
```

## 3. Events: Upstash Redis

Create one Upstash Redis database. Put its TLS URL into Render:

```bash
REDIS_URL=rediss://...
```

The API publishes after persistence succeeds:

- `response.scored`
- `flag.created`
- `trust.updated`
- `sandbox.turn`

## 4. Frontend: Vercel

The Vercel project uses:

```json
{
  "buildCommand": "cd apps/web && npm run build",
  "outputDirectory": "apps/web/dist"
}
```

Set Vercel production env:

```bash
BACKEND_URL=https://<render-service>.onrender.com
```

Deploy:

```bash
npx vercel --prod --yes
```

The frontend calls `/api/*`; Vercel proxies those requests to `BACKEND_URL`.

## 5. WhatsApp: Meta Cloud API

Meta webhook URL:

```bash
https://<render-service>.onrender.com/api/v1/channels/whatsapp/webhook
```

Use the same `WHATSAPP_VERIFY_TOKEN` in Meta and Render.

Flow:

1. Citizen sends `Hi`.
2. Meta sends webhook to SATARK backend.
3. Backend starts or resumes the latest published survey session.
4. Backend asks one survey question at a time.
5. Each answer goes through the same deterministic collection/intelligence pipeline.
6. Final response persists to Postgres, trust is stored, events are emitted.

## 6. Final Smoke Test

Run these after Render and Vercel are both live:

```bash
curl https://<render-service>.onrender.com/health/ready
curl https://<vercel-app>.vercel.app/api/health/ready
```

Then in the browser:

1. Log in to Vercel frontend.
2. Generate and publish a survey from SDRD.
3. Verify it appears in FOD and collection.
4. Start WhatsApp with `Hi`; answer all questions.
5. Confirm DPD queue and SCD dashboard show the persisted response and trust score.

## Notes

- Render free services may sleep after inactivity, causing a cold start on the
  first request.
- `LLM_REQUIRED=false` is intentional. If OpenRouter quota/model availability
  fails, survey assist falls back to deterministic generation and still marks
  output as `needs_review`.
- Verdict/trust scoring never depends on the LLM. The LLM is assist-only.
