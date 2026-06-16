"""Channel-agnostic survey loop.

IVR, WhatsApp and the AI avatar all drive a survey through the SAME intelligence
pipeline: one question out, one answer in, validate, next question out.  The
channel adapters are thin I/O — they serialise questions out and normalise
answers in; they NEVER score.

Every answer is scored by the single deterministic entry point
``evaluate_intelligence_contract`` (the orchestrator wrapper) — exactly the
function the web collection client uses.  There is no second validation path.
The final response is sealed through the existing ``store_collection_response``
persistence path, so responses/audit_logs stay append-only and every persisted
verdict keeps its reason.  Assist outputs (code suggestions) keep is_verdict:false.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import HTTPException

from app import channel_sessions, sandbox_feed
from models.platform import IntelligenceSession
from services.collection_service import (
    _active_rules_for_answers,
    _adaptive_logic,
    _enumerator_context,
    _expanded_questions,
    _graph_decision,
    _load_survey,
    _next_unanswered,
    _reference,
    _survey_graph,
    _with_decision,
)
from services.events import RedisPublishError, publish_intelligence_events
from services.intelligence_adapter import evaluate_intelligence_contract
from services.response_service import store_collection_response

VALID_CHANNELS = {"whatsapp", "ivr", "avatar", "web"}
CONSENT_NODE = "__consent__"

CONSENT_PROMPT = {
    "en": "Do you consent to take part in this official survey? Reply Yes or No.",
    "hi": "क्या आप इस आधिकारिक सर्वेक्षण में भाग लेने के लिए सहमत हैं? हाँ या नहीं उत्तर दें।",
    "ta": "இந்த அதிகாரப்பூர்வ கணக்கெடுப்பில் பங்கேற்க ஒப்புக்கொள்கிறீர்களா? ஆம் அல்லது இல்லை எனப் பதிலளிக்கவும்.",
}


# ---------------------------------------------------------------------------
# Public API (called by the channel routes)
# ---------------------------------------------------------------------------

def start_session(db, payload: dict[str, Any]) -> dict[str, Any]:
    survey_id = str(payload.get("survey_id") or payload.get("surveyId") or "").strip()
    channel = _channel(payload.get("channel"))
    respondent_ref = str(payload.get("respondent_ref") or payload.get("respondentRef") or "").strip()
    if not survey_id or not respondent_ref:
        raise HTTPException(status_code=400, detail="survey_id and respondent_ref are required")

    survey = _load_survey(db, survey_id)
    graph = _survey_graph(survey)

    row = IntelligenceSession(
        survey_id=survey_id,
        household_id=payload.get("household_id") or payload.get("householdId"),
        enumerator_id=payload.get("enumerator_id") or payload.get("enumeratorId"),
        status="active",
        payload={"channel": channel, "respondent_ref": respondent_ref, "kind": "channel-session"},
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    state = {
        "session_id": str(row.id),
        "response_id": None,
        "survey_id": survey_id,
        "channel": channel,
        "respondent_ref": respondent_ref,
        "household_id": payload.get("household_id") or payload.get("householdId"),
        "enumerator_id": payload.get("enumerator_id") or payload.get("enumeratorId"),
        "lang": payload.get("lang") or payload.get("language") or "en",
        "consent": False,
        "current_node": CONSENT_NODE,
        "answers": {},
        "timings": {},
        "correction_count": 0,
        "last_sent_at": _now(),
        "status": "active",
        "last_result": None,
    }
    channel_sessions.save(channel, respondent_ref, state)
    return _outbound_consent(state)


def answer(db, payload: dict[str, Any]) -> dict[str, Any]:
    channel = _channel(payload.get("channel"))
    respondent_ref = str(payload.get("respondent_ref") or payload.get("respondentRef") or "").strip()
    raw_answer = payload.get("raw_answer")
    if raw_answer is None:
        raw_answer = payload.get("rawAnswer")
    meta = payload.get("meta") or {}

    state = channel_sessions.load(channel, respondent_ref)
    if not state:
        raise HTTPException(status_code=404, detail="No active channel session for this respondent")
    if state.get("status") != "active":
        raise HTTPException(status_code=409, detail=f"Channel session is {state.get('status')}")

    survey = _load_survey(db, state["survey_id"])
    graph = _survey_graph(survey)
    elapsed = _elapsed_for_turn(state, meta)
    current = state["current_node"]

    # --- consent gate -----------------------------------------------------
    if current == CONSENT_NODE:
        if not _truthy(raw_answer):
            state["status"] = "declined"
            channel_sessions.save(channel, respondent_ref, state)
            return _outbound_complete(state, None, {"declined": True, "reason": "Respondent declined consent"})
        state["consent"] = True
        order = _expanded_questions(graph, state["answers"])
        nxt = _next_unanswered(order, state["answers"])
        state["current_node"] = nxt["id"] if nxt else CONSENT_NODE
        state["last_sent_at"] = _now()
        channel_sessions.save(channel, respondent_ref, state)
        if not nxt:
            return _outbound_complete(state, None, {"reason": "Survey has no questions"})
        return _outbound_question(state, nxt, last_result=None, adaptive=None)

    # --- a question answer ------------------------------------------------
    node = _find_node(graph, current, state["answers"])
    if node is None:
        raise HTTPException(status_code=409, detail=f"Current node '{current}' is not in the survey graph")
    if current in state["answers"]:
        state["correction_count"] = int(state.get("correction_count", 0)) + 1
    typed = _coerce(node, raw_answer)
    state["answers"][current] = typed
    state["timings"][current] = max(1, int(round(elapsed)))

    speed_mode = "too-fast" if elapsed <= 5 else "normal"
    intelligence = evaluate_intelligence_contract(
        answers=state["answers"],
        active_question_id=current,
        speed_mode=speed_mode,
        elapsed_seconds=elapsed,
        rules=_active_rules_for_answers(db, state["survey_id"], state["answers"]),
        reference=_reference(db, state["answers"]),
        enumerator=_enumerator_context(db, state.get("enumerator_id")),
        adaptive_logic=_adaptive_logic(db, state["survey_id"]),
    )

    # next-node decision (graph branch first, then orchestrator adaptive action)
    order = _expanded_questions(graph, state["answers"])
    nxt = _next_unanswered(order, state["answers"])
    graph_decision = _graph_decision(graph, current, typed, nxt)
    if graph_decision:
        intelligence = _with_decision(intelligence, graph_decision)
    elif nxt:
        intelligence = _with_decision(
            intelligence,
            {
                "action": intelligence.get("decision") if intelligence.get("decision") in {"SIMPLIFY", "REORDER"} else "ASK",
                "target": nxt["id"],
                "reason": intelligence.get("reason") or f"asking {nxt['id']} next",
                "params": {},
            },
        )
    state["last_result"] = intelligence

    clarify = _clarification_layer(intelligence, node)
    finishing = nxt is None and not clarify

    # publish the verdict events + the sandbox turn for the live readout.
    # On the final turn we let store_collection_response publish so we do not
    # double-fire; sandbox.turn always fires (it is the live-loop signal).
    if not finishing:
        _safe_publish_events(intelligence.get("events", []), _event_payload(state, intelligence))
    sandbox_feed.record_turn(_sandbox_turn(state, current, node, typed, intelligence))

    if clarify:
        state["last_sent_at"] = _now()
        channel_sessions.save(channel, respondent_ref, state)
        return _outbound_clarification(state, node, intelligence, clarify)

    if finishing:
        result = _finalize(db, state, intelligence)
        state["status"] = "completed"
        state["response_id"] = result.get("responseId")
        channel_sessions.save(channel, respondent_ref, state)
        return _outbound_complete(state, intelligence, result)

    state["current_node"] = nxt["id"]
    state["last_sent_at"] = _now()
    channel_sessions.save(channel, respondent_ref, state)
    return _outbound_question(state, nxt, last_result=intelligence, adaptive=intelligence.get("adaptive"))


def inbound(db, channel: str, respondent_ref: str, raw_answer: Any, meta: dict[str, Any] | None = None, survey_id: str | None = None) -> dict[str, Any]:
    """Real-channel entry point: auto-starts a session on first contact, then
    answers. This is what the live WhatsApp/IVR/avatar bridges call so a citizen
    simply messaging in drives the SAME one-pipeline loop (and shows in the
    Enumerator Sandbox)."""
    channel = _channel(channel)
    respondent_ref = str(respondent_ref or "").strip()
    state = channel_sessions.load(channel, respondent_ref)
    if not state or state.get("status") != "active":
        return start_session(db, {"survey_id": survey_id or _default_survey_id(db), "channel": channel, "respondent_ref": respondent_ref})
    return answer(db, {"channel": channel, "respondent_ref": respondent_ref, "raw_answer": raw_answer, "meta": meta or {}})


def _default_survey_id(db) -> str:
    from models.survey import Survey

    rows = (
        db.query(Survey)
        .filter(Survey.status == "published")
        .order_by(Survey.created_at.desc())
        .all()
    )
    if rows:
        latest = rows[0]
        companion = _fuller_generated_companion(latest, rows)
        return companion.survey_id if companion else latest.survey_id
    raise HTTPException(status_code=409, detail="No published survey is available for channel collection")


def _fuller_generated_companion(latest, rows):
    """Prefer a generated published draft when the newest row is only a shell.

    SDRD can publish a DDI shell row (for the national survey identity) and a
    generated source-traced draft row (``<survey>-DRAFT-*``) for the actual
    questionnaire. Channels must collect the questionnaire, not stop at the
    shell's few demographic nodes.
    """
    latest_count = _survey_node_count(latest)
    if latest_count > 5:
        return None
    prefix = f"{latest.survey_id}-DRAFT-"
    companions = [row for row in rows if str(row.survey_id).startswith(prefix) and _survey_node_count(row) > latest_count]
    if not companions:
        return None
    return sorted(
        companions,
        key=lambda row: (
            row.published_at or row.updated_at or row.created_at,
            _survey_node_count(row),
        ),
        reverse=True,
    )[0]


def _survey_node_count(row) -> int:
    graph = row.question_graph or row.survey_data or {}
    if isinstance(graph, dict):
        nodes = graph.get("nodes") or []
        if isinstance(nodes, list):
            return len([node for node in nodes if isinstance(node, dict) and node.get("id")])
    return int(row.total_questions or 0)


def current_payload(db, channel: str, respondent_ref: str) -> dict[str, Any]:
    """Idempotent re-fetch of the current outbound payload (does not advance)."""
    channel = _channel(channel)
    state = channel_sessions.load(channel, respondent_ref)
    if not state:
        raise HTTPException(status_code=404, detail="No active channel session for this respondent")
    if state.get("status") == "completed":
        return _outbound_complete(state, state.get("last_result"), {"reason": "Session already complete"})
    if state.get("current_node") == CONSENT_NODE:
        return _outbound_consent(state)
    survey = _load_survey(db, state["survey_id"])
    graph = _survey_graph(survey)
    node = _find_node(graph, state["current_node"], state["answers"])
    if node is None:
        raise HTTPException(status_code=409, detail="Current node is not in the survey graph")
    return _outbound_question(state, node, last_result=state.get("last_result"), adaptive=(state.get("last_result") or {}).get("adaptive"))


# ---------------------------------------------------------------------------
# Finalisation — reuse the single persistence path (append-only Response)
# ---------------------------------------------------------------------------

def _finalize(db, state: dict[str, Any], intelligence: dict[str, Any]) -> dict[str, Any]:
    timings = state.get("timings") or {}
    total = sum(int(v or 0) for v in timings.values())
    too_fast = any(int(v or 0) <= 5 for v in timings.values())
    elapsed = min([int(v or 0) for v in timings.values()] or [90])
    return store_collection_response(
        db,
        {
            "surveyId": state["survey_id"],
            "householdId": state.get("household_id"),
            "enumeratorId": state.get("enumerator_id"),
            "answers": state["answers"],
            "prepopulated": {},
            "intelligence": intelligence,
            "verdictSource": "session",
            "speedMode": "too-fast" if too_fast else "normal",
            "elapsedSeconds": elapsed,
            "durationSeconds": total or None,
            "channel": state["channel"],
            "correctionCount": state.get("correction_count", 0),
            "mode": "channel",
        },
        event_publisher=_safe_publish_events,
    )


# ---------------------------------------------------------------------------
# Outbound payload builders (channel-neutral schema)
# ---------------------------------------------------------------------------

def _outbound_consent(state: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "type": "consent",
        "channel": state["channel"],
        "session_id": state["session_id"],
        "node_id": CONSENT_NODE,
        "prompt_text": dict(CONSENT_PROMPT),
        "input_kind": "choice",
        "options": [
            {"value": "yes", "label_i18n": {"en": "Yes", "hi": "हाँ", "ta": "ஆம்"}},
            {"value": "no", "label_i18n": {"en": "No", "hi": "नहीं", "ta": "இல்லை"}},
        ],
    }
    _attach_channel_helpers(state, payload)
    return payload


def _outbound_question(state, node, last_result=None, adaptive=None) -> dict[str, Any]:
    payload = {
        "type": "question",
        "channel": state["channel"],
        "session_id": state["session_id"],
        "node_id": node["id"],
        "prompt_text": _prompt_text(node),
        "input_kind": _input_kind(node),
        "options": _options(node),
    }
    _attach_channel_helpers(state, payload)
    if adaptive:
        payload["adaptive"] = {"action": adaptive.get("action"), "reason": adaptive.get("reason")}
    if last_result:
        payload["last_result"] = _last_result(last_result)
        payload["events"] = last_result.get("events", [])
    return payload


def _outbound_clarification(state, node, intelligence, layer) -> dict[str, Any]:
    payload = {
        "type": "clarification",
        "channel": state["channel"],
        "session_id": state["session_id"],
        "node_id": node["id"],
        "prompt_text": {
            key: f"{layer['reason']} — {value}" for key, value in _prompt_text(node).items()
        },
        "input_kind": _input_kind(node),
        "options": _options(node),
        "adaptive": {"action": intelligence.get("adaptive", {}).get("action"), "reason": layer["reason"]},
        "last_result": _last_result(intelligence),
        "events": intelligence.get("events", []),
    }
    _attach_channel_helpers(state, payload)
    return payload


def _outbound_complete(state, intelligence, result) -> dict[str, Any]:
    payload = {
        "type": "complete",
        "channel": state["channel"],
        "session_id": state["session_id"],
        "node_id": None,
        "prompt_text": {
            "en": "Thank you. The survey is complete.",
            "hi": "धन्यवाद। सर्वेक्षण पूर्ण हो गया है।",
            "ta": "நன்றி. கணக்கெடுப்பு முடிந்தது.",
        },
        "input_kind": "text",
        "result": result,
    }
    if intelligence:
        payload["last_result"] = _last_result(intelligence)
        payload["events"] = intelligence.get("events", [])
    _attach_channel_helpers(state, payload)
    return payload


def _attach_channel_helpers(state: dict[str, Any], payload: dict[str, Any]) -> None:
    lang = state.get("lang", "en")
    prompt = payload.get("prompt_text") or {}
    speak = prompt.get(lang) or prompt.get("en") or ""
    options = payload.get("options")
    channel = state["channel"]
    if channel == "ivr":
        if options and payload.get("type") != "complete":
            spoken_opts = " ".join(
                f"Press {idx + 1} for {opt['label_i18n'].get(lang) or opt['label_i18n']['en']}."
                for idx, opt in enumerate(options)
            )
            payload["speak_text"] = f"{speak} {spoken_opts}".strip()
            payload["expect"] = "dtmf"
        else:
            payload["speak_text"] = speak
            payload["expect"] = "speech" if payload.get("type") != "complete" else "none"
    elif channel == "avatar":
        payload["tts_text"] = speak
        payload["speak_text"] = speak
        payload["expect"] = "voice" if payload.get("type") != "complete" else "none"


def _prompt_text(node: dict[str, Any]) -> dict[str, str]:
    q = node.get("q") or node.get("prompt_text") or {}
    if isinstance(q, dict):
        en = q.get("en") or q.get("hi") or q.get("ta") or str(node.get("id"))
        return {"en": en, "hi": q.get("hi") or en, "ta": q.get("ta") or en}
    text = str(q)
    return {"en": text, "hi": text, "ta": text}


def _input_kind(node: dict[str, Any]) -> str:
    return {"choice": "choice", "multi": "choice", "number": "number", "text": "text", "date": "text"}.get(
        str(node.get("type")), "text"
    )


def _options(node: dict[str, Any]) -> Optional[list[dict[str, Any]]]:
    options = node.get("options")
    if not options:
        return None
    out = []
    for opt in options:
        if isinstance(opt, dict):
            value = opt.get("value") or opt.get("label")
            label = opt.get("label") or opt.get("value")
        else:
            value = opt
            label = opt
        out.append({"value": value, "label_i18n": {"en": str(label), "hi": str(label), "ta": str(label)}})
    return out


def _last_result(intelligence: dict[str, Any]) -> dict[str, Any]:
    return {
        "confidence": intelligence.get("confidence"),
        "risk_level": intelligence.get("trustLevel"),
        "layers": [
            {
                "name": layer["layer"],
                "status": layer["status"],
                "reason": layer["reason"],
                "confidence": layer.get("confidence"),
                "method": layer.get("method"),
                "flagged": layer.get("flagged"),
            }
            for layer in intelligence.get("layers", [])
        ],
        "methods": intelligence.get("methods", []),
        "flaggedBy": intelligence.get("flaggedBy", []),
    }


# ---------------------------------------------------------------------------
# Answer normalisation (thin I/O — no scoring)
# ---------------------------------------------------------------------------

def _coerce(node: dict[str, Any], raw_answer: Any) -> Any:
    kind = str(node.get("type"))
    raw = "" if raw_answer is None else str(raw_answer).strip()
    if kind in {"choice", "multi"}:
        options = node.get("options") or []
        labels = [o.get("label") or o.get("value") if isinstance(o, dict) else o for o in options]
        # exact (case-insensitive) match
        for label in labels:
            if raw.lower() == str(label).lower():
                return label
        # DTMF / numeric index (1-based)
        if raw.isdigit():
            idx = int(raw) - 1
            if 0 <= idx < len(labels):
                return labels[idx]
        # single-letter index (a, b, c ...)
        if len(raw) == 1 and raw.isalpha():
            idx = ord(raw.lower()) - ord("a")
            if 0 <= idx < len(labels):
                return labels[idx]
        return raw
    if kind == "number":
        try:
            number = float(raw.replace(",", ""))
            return int(number) if number.is_integer() else number
        except (TypeError, ValueError):
            return raw
    return raw


def _truthy(raw_answer: Any) -> bool:
    raw = str(raw_answer or "").strip().lower()
    return raw in {"yes", "y", "1", "true", "ok", "consent", "agree", "ஆம்", "हाँ", "haan", "haa"}


def _find_node(graph: dict[str, Any], node_id: str, answers: dict[str, Any]) -> Optional[dict[str, Any]]:
    for node in _expanded_questions(graph, answers):
        if node.get("id") == node_id:
            return node
    return None


# ---------------------------------------------------------------------------
# Clarification — only genuine data-entry errors re-ask; fraud signals flag.
# ---------------------------------------------------------------------------

def _clarification_layer(intelligence: dict[str, Any], node: dict[str, Any]) -> Optional[dict[str, Any]]:
    kind = str(node.get("type"))
    for layer in intelligence.get("layers", []):
        if layer.get("status") != "fail":
            continue
        name = layer.get("layer")
        if name == "Completeness":
            return layer
        if name == "Range" and kind == "number":
            return layer
    return None


# ---------------------------------------------------------------------------
# Events / sandbox helpers
# ---------------------------------------------------------------------------

def _event_payload(state: dict[str, Any], intelligence: dict[str, Any]) -> dict[str, Any]:
    native = intelligence.get("native_trust") or {}
    return {
        "response_id": state.get("response_id"),
        "session_id": state["session_id"],
        "channel": state["channel"],
        "enumerator_id": state.get("enumerator_id"),
        "confidence": intelligence.get("confidence"),
        "risk_level": intelligence.get("trustLevel"),
        "reasons": (native.get("reasons") or [])[:3],
    }


def _sandbox_turn(state, node_id, node, typed, intelligence) -> dict[str, Any]:
    return {
        "session_id": state["session_id"],
        "channel": state["channel"],
        "respondent_ref": state["respondent_ref"],
        "node_id": node_id,
        "question": _prompt_text(node).get(state.get("lang", "en")),
        "answer": typed,
        "result": {
            "confidence": intelligence.get("confidence"),
            "risk_level": intelligence.get("trustLevel"),
            "layers": [
                {
                    "name": layer["layer"],
                    "status": layer["status"],
                    "reason": layer["reason"],
                    "confidence": layer.get("confidence"),
                    "method": layer.get("method"),
                    "flagged": layer.get("flagged"),
                }
                for layer in intelligence.get("layers", [])
            ],
            "methods": intelligence.get("methods", []),
            "flaggedBy": intelligence.get("flaggedBy", []),
            "reasons": (intelligence.get("native_trust") or {}).get("reasons", [])[:3],
            "scores": intelligence.get("scores", {}),
        },
        "adaptive": intelligence.get("adaptive", {}),
    }


def _safe_publish_events(events: list[str], payload: dict[str, Any]) -> list[str]:
    """Best-effort verdict event publish — works with or without Redis.

    Skips the publish path when Redis is unavailable (cached probe) so we never
    pay a refused-connection per turn; the returned event list still lets the
    caller (and tests) observe what *would* be emitted.
    """
    if not events:
        return []
    if channel_sessions.backend() != "redis":
        return events
    try:
        return publish_intelligence_events(events, payload)
    except RedisPublishError:
        return events
    except Exception:  # noqa: BLE001
        return events


def _channel(value: Any) -> str:
    channel = str(value or "").strip().lower()
    if channel not in VALID_CHANNELS:
        raise HTTPException(status_code=400, detail=f"channel must be one of {sorted(VALID_CHANNELS)}")
    return channel


def _elapsed_for_turn(state: dict[str, Any], meta: dict[str, Any]) -> float:
    explicit = meta.get("elapsed_seconds") or meta.get("elapsedSeconds")
    if explicit:
        try:
            return max(1.0, float(explicit))
        except (TypeError, ValueError):
            pass
    last_sent = state.get("last_sent_at")
    if last_sent:
        try:
            then = datetime.fromisoformat(last_sent)
            now = datetime.now(timezone.utc)
            if then.tzinfo is None:
                then = then.replace(tzinfo=timezone.utc)
            return max(1.0, (now - then).total_seconds())
        except (TypeError, ValueError):
            pass
    return 90.0


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
