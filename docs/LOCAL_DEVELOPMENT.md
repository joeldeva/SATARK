# Local Development

## Prerequisites

- Python 3.10+
- Node.js 20+
- Ollama with `llama3.2:3b`

```powershell
ollama pull llama3.2:3b
```

## Backend

```powershell
cd apps/api
python -m pip install -r requirements.txt
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
