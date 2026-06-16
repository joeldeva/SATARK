# SATARK — Deployment

## Reality constraint

Firebase Hosting serves **static files only**. Postgres, Redis, Chroma, Ollama and
the FastAPI app **cannot** run on Firebase. Deployment is therefore split:

- **Frontend + landing page → Firebase Hosting** (static).
- **Backend (FastAPI + Postgres + Redis + Ollama) → the demo machine**, exposed to the
  hosted frontend through a tunnel (cloudflared or ngrok).

> **Demo-day primary plan is the LOCAL machine, end to end.** The Firebase URL is the
> shareable mirror, not the stage plan. The hosted frontend only works while the tunnel
> to the backend is running.

---

## 1. Frontend + landing → Firebase Hosting

The hosting payload puts the **landing page at `/`** and the **SPA at `/app/**`**.

```bash
cd apps/web
npm install
# Point the SPA at the tunneled backend (see step 2). For a local-only build, omit it.
echo "VITE_API_URL=https://<your-tunnel-host>" > .env.production
npm run build:hosting      # vite build (base=/app/) + assemble dist/  (landing at /, SPA at /app)

cd ..                      # repo root that holds firebase.json
firebase login
firebase init hosting      # public dir = apps/web/dist  (already set in firebase.json)
firebase deploy --only hosting
```

`firebase.json` (already in the repo) does the routing:

```json
{
  "hosting": {
    "public": "apps/web/dist",
    "rewrites": [{ "source": "/app/**", "destination": "/app/index.html" }]
  }
}
```

- `/`              → `dist/index.html`  (the GoI-standard landing page)
- `/app`, `/app/*` → `dist/app/index.html` (the React SPA; login at `/app`)
- Landing "Open Platform" / "Launch Workspace" buttons link to `/app`.

## 2. Backend on the demo machine + tunnel

```bash
cd SATARKoff-main
docker compose up -d                  # Postgres + Redis + API (+ Ollama if configured)

# expose the API publicly
cloudflared tunnel --url http://localhost:8001
#   or: ngrok http 8001
# -> note the stable public URL, e.g. https://abc-123.trycloudflare.com
```

Set that URL as `VITE_API_URL` for the Firebase build (step 1) and add the **Firebase
origin** to the backend CORS allowlist:

```bash
# on the backend host (.env or compose env)
export CORS_ORIGINS="https://<your-project>.web.app,https://<your-project>.firebaseapp.com,http://localhost:3001"
```

The WebSocket endpoint (`/api/events/live`, `/api/dashboard/live`,
`/api/v1/sandbox/live`) works through the tunnel — the SPA derives the `wss://` URL from
`VITE_API_URL`, so verify the SCD command-center live feed connects after deploy. If the
tunnel/WS is unavailable, the dashboards fall back to 3-second polling.

## 3. End-to-end check from the Firebase URL

1. Open `https://<project>.web.app/` → landing renders; click **Open Platform** → `/app`.
2. Log in (e.g. `fod` / `field123`); the role-correct workspace loads.
3. Run the suspicious flow (Unemployed + ₹2,00,000, fast) → returns ~46 confidence **Red**
   with reasons; the **flag.created** event appears on the SCD live feed within ~5s.

## 4. Local-only demo (primary plan)

```bash
# backend
cd SATARKoff-main && docker compose up -d
# frontend (dev)
cd apps/web && npm install && npm run dev   # http://127.0.0.1:3001/app/
# landing (static)
python -m http.server 4178 --directory "../../landing page"   # http://127.0.0.1:4178/
```

Everything (Postgres, Redis, Ollama, Chroma) runs on the one machine; no tunnel needed.

## Notes

- `RAG_EMBEDDINGS=st` switches the assist RAG lane to the neural
  `paraphrase-multilingual-MiniLM-L12-v2` model once it is available locally; otherwise
  the offline lexical-semantic embedding is used (RAG still works, no network needed).
- Chroma is optional: without it, the assist lane uses a persisted local vector store
  under `data/chroma/` that survives restarts.
