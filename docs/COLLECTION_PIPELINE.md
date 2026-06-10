# SATARK Collection Pipeline

SATARK collection is now backend-authoritative. The browser renders the form and captures timing, but it does not decide the next question, trust level, fraud flag, or final score.

## Runtime Flow

1. Field Operations assigns a published survey to an enumerator.
2. The Collection Client starts a session through `POST /api/collection/sessions/start`.
3. The API loads the assignment, survey graph, household context, enumerator profile, validation rules, reference distributions, and any existing session state.
4. The API returns the first active question plus the server-owned visible queue.
5. For every answer, the browser sends:
   - `questionId`
   - `value`
   - `elapsedSeconds`
   - optional correction/back-navigation counters
6. The API stores the answer in the `intelligence_sessions.payload` event log.
7. The adaptive engine recomputes the visible queue and next question from the survey graph and current answers.
8. The verdict adapter scores only the answered fields with deterministic rule, context, behaviour, Bayesian, and trust engines.
9. The API returns the next question and the full intelligence result to the browser.
10. On completion, `POST /api/collection/sessions/{session_id}/complete` writes the response, paradata, validation rows, and trust score to Postgres.
11. Only after persistence succeeds, Redis emits:
    - `response.scored`
    - `flag.created`
    - `trust.updated`
12. Dashboards read Postgres for durable truth and Redis for live updates.

## Adaptive Rules

Adaptive branching happens on the backend. For example, when `occupation = Student`, the server inserts the `institution` branch question into the active queue. The UI cannot skip the branch by changing local state because the next question comes from the session endpoint.

Every adaptive decision is returned with a plain-language reason in `intelligence.reason` and is stored in the session event log.

## Verdict Boundary

The verdict lane is deterministic and auditable:

- `app/intelligence/orchestrator.py`
- `app/intelligence/verdict/*`
- `services/intelligence_adapter.py`
- `services/collection_service.py`
- `services/response_service.py`

It cannot import Assist, RAG, LLM, Gemma, Ollama, or LangChain modules. `tests/test_import_guard.py` blocks that boundary.

## Assist Boundary

The assist lane is suggest-only:

- survey prompt planning
- draft question creation
- RAG context lookup
- local Gemma calls through Ollama
- LangChain-compatible prompt rendering

Assist output must carry:

```json
{
  "needs_review": true,
  "is_verdict": false
}
```

Survey generation remains human-review only. SDRD must publish before Field Operations can assign and collect.

## SuperPlane Boundary

SATARK follows SuperPlane's event-driven workflow idea without making it a hard runtime dependency.

Configure these environment variables only when a SuperPlane-compatible workflow receiver exists:

```env
SUPERPLANE_WEBHOOK_URL=http://localhost:3000/webhooks/satark
SUPERPLANE_TOKEN=optional-secret
```

When configured, SATARK sends the same post-persistence events that Redis receives. If the webhook is down, the API logs a warning and keeps the saved response intact. Workflow orchestration can never block verdict storage.

## LangChain Boundary

SATARK uses `langchain-core` prompt templates in the assist lane to structure local Gemma prompts. It does not use LangChain hosted services, external LLM APIs, or LangSmith.

If `langchain-core` is unavailable, the local prompt renderer falls back to Python formatting and keeps the same offline behaviour.

## Postgres Storage

Postgres stores durable survey operations:

- `surveys`: published survey definitions and graphs
- `assignments`: survey-to-enumerator assignment state
- `intelligence_sessions`: in-progress collection events and adaptive state
- `responses`: final submitted answer payload
- `paradata`: timing, speed, correction, and navigation evidence
- `validation_results`: rule, cross-field, context, and behaviour results
- `trust_scores`: final confidence, trust level, and reasons

Dashboards and review screens read these tables. Redis is used only for live notification, not as the source of truth.
