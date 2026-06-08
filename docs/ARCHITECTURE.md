# Architecture

SATARK has one active backend, one active frontend, and shared data resources.

## Backend

`apps/api` exposes a FastAPI app with:

- `/api` role-based demo auth
- `/api` survey, question bank, code library, enumerator, analytics, coding, consent, prepopulate, intelligence, export, and response endpoints
- `/api/v1` compatibility routes for the earlier generator endpoints
- local Ollama Gemma assist planning with `gemma2:2b`
- Postgres-first platform persistence for surveys, responses, paradata, validation rows, trust scores, users, roles, enumerators, households, codes, and reference distributions
- Redis event publishing after persisted verdicts for `response.scored`, `flag.created`, and `trust.updated`
- deterministic parser available only when `LLM_PROVIDER=none`
- keyword retrieval from trusted local question sources
- shared seed data from `data/demo_seed.json`

The optional vector-search dependencies are not required. If `sentence_transformers` and `chromadb` are installed, retrieval can use vector mode; otherwise the keyword retriever is used.

## Frontend

`apps/web` is a Vite React app with:

- React 18, TypeScript, Tailwind, React Router, React Query, Zustand, i18next, Recharts, lucide-react
- role-based login and workspace routing
- official-style SATARK app shell with language, color-blind mode, font size controls, sync status, and workspace badge
- SDRD survey builder, FOD field operations, DPD coding/validation, SCD command center, and collection client
- PWA manifest, service worker, and IndexedDB offline queue
- seed fallback for every API call

The frontend uses `VITE_API_URL` and defaults to `/api`. During local Vite development, `/api` is proxied to `http://127.0.0.1:8001`.

## Data And Infra

`data/demo_seed.json` is the role-based product demo source. `data/question_bank/question_bank.json` and `data/knowledge_base` remain the trusted generation and knowledge sources.

Local infrastructure is defined in `docker-compose.yml`:

- Postgres 16 for durable application data
- Redis 7 for verdict/event streams
- Chroma for the later assist/RAG lane

SQLite remains a developer fallback when `DATABASE_URL` is not pointed at Postgres, but migrations are authored for a fresh Postgres schema with native UUID and JSONB types.

## Local LLM Boundary

The model is private and local:

```text
User prompt -> LocalLLMPlanner -> ParsedIntent + draft questions -> RAGEngine -> RuleEngine -> SurveyGenerator
```

Default config:

- `LLM_PROVIDER=ollama`
- `LLM_MODEL=gemma2:2b`
- `OLLAMA_BASE_URL=http://127.0.0.1:11434`
- `LLM_REQUIRED=true`

No survey prompt or response data is sent to an external API. The LLM extracts intent and proposes draft questions for prompt-specific coverage; SATARK still owns final validation, ordering, required demographics, and provenance metadata.

Assist outputs are always marked `is_verdict: false`. Deterministic verdict services do not import assist, RAG, LLM, Gemma, or Ollama modules.
