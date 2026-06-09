# Local Development

## Prerequisites

- Python 3.10+
- Node.js 20+
- Docker Desktop for Postgres, Redis, and Chroma
- Ollama with `gemma2:2b`

```powershell
ollama pull gemma2:2b
```

## Backend

Start local infrastructure:

```powershell
Copy-Item .env.example .env
docker compose up -d postgres redis chroma
```

Or run the complete backend stack in Docker. Ollama still runs on the host with `gemma2:2b`, and the API container reaches it through `host.docker.internal`.

```powershell
docker compose up -d postgres redis chroma api
```

```powershell
cd apps/api
python -m pip install -r requirements.txt
python -m alembic upgrade head
python -m uvicorn main:app --host 127.0.0.1 --port 8001
```

Useful endpoints:

- `GET /health`
- `POST /api/auth/login`
- `GET /api/surveys`
- `POST /api/surveys/generate`
- `GET /api/question-bank`
- `GET /api/codes`
- `GET /api/llm/status`
- `GET /api/enumerators`
- `POST /api/intelligence/answer`
- `GET /api/analytics`
- `POST /api/responses`
- `POST /api/v1/generate`

## Frontend

```powershell
cd apps/web
npm install
$env:VITE_API_URL="/api"
npm run dev -- --port 3001
```

Open http://localhost:3001.

## Tests And Checks

```powershell
cd apps/api
python test_core.py

cd ../web
npm run typecheck
npm audit --audit-level=low
npm run build
```

## Deployment Runtime

Vercel is only the frontend/proxy path. FastAPI, Postgres, Redis, Chroma, Ollama, and `gemma2:2b` must run on one reachable local machine or VM.
