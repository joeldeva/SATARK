# SATARK

SATARK is an adaptive survey intelligence platform for trusted official statistics. It is now arranged as one installable PWA, one FastAPI backend, shared seed data, and focused documentation.

Survey generation uses a private local Gemma assist planner by default:

- Runtime: Ollama
- Model: `gemma2:2b`
- Privacy: local inference only, no external API
- Role: intent and prompt-specific draft question planning; SATARK still controls validation, ordering, metadata, and trusted-rule application

## Project Layout

```text
apps/
  api/    FastAPI backend, Postgres-first persistence, SATARK API contract
  web/    React 18 + TypeScript + Tailwind PWA
data/
  bootstrap_seed.json   initial users, roles, enumerators, survey, codes, personas, trust rules
  knowledge_base/  curated survey and validation-rule data
  question_bank/   normalized source question bank
docs/
  ARCHITECTURE.md
  LOCAL_DEVELOPMENT.md
```

## Run Locally

Infra:

```powershell
docker compose up -d postgres redis chroma
```

Complete backend stack:

```powershell
$env:SATARK_SECRET_KEY="<long-random-secret>"
docker compose up -d postgres redis chroma api
```

Backend:

```powershell
ollama pull gemma2:2b
cd apps/api
python -m uvicorn main:app --host 127.0.0.1 --port 8001
```

Frontend:

```powershell
cd apps/web
npm install
$env:PORT="3001"; npm run dev -- --port 3001
```

Open http://localhost:3001.

API docs are available at http://localhost:8001/docs.

For deployment, Vercel can host the frontend/proxy only. FastAPI, Postgres, Redis, Chroma, Ollama, and `gemma2:2b` must run on a reachable backend machine or VM.

## Demo Login

| Role | Username | Password |
| --- | --- | --- |
| Admin | `admin` | `admin123` |
| SDRD | `sdrd` | `design123` |
| FOD | `fod` | `field123` |
| DPD | `dpd` | `process123` |
| SCD | `scd` | `coord123` |

## Workspaces

- SDRD: survey builder, question bank, code library
- FOD: enumerators, assignments, trust drill-down
- DPD: coding review, validation queue
- SCD: command center, quality dashboard, analytics
- Collection client: language, consent, conversational survey, live Intelligence Panel, offline queue

## Local LLM Flow

```text
Prompt -> Ollama gemma2:2b -> strict intent + draft questions -> question retrieval -> SATARK rules -> final survey
```

The LLM extracts intent and proposes draft questions for prompt-specific coverage. Final validation, ordering, required demographics, provenance metadata, and trusted-rule application remain controlled by SATARK.

## Verification

```powershell
cd apps/api
python test_core.py

cd ../web
npm run typecheck
npm audit --audit-level=low
npm run build
```
