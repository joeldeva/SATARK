from __future__ import annotations

import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends, Header, HTTPException

from app.config import settings
from models.platform import Assignment, EnumeratorProfile, IntelligenceSession
from services.collection_service import answer_session, complete_session, start_session

logger = logging.getLogger(__name__)
router = APIRouter()

_get_db = None


def set_db_dependency(get_db_func):
    global _get_db
    _get_db = get_db_func


def _open_db():
    if not _get_db:
        raise HTTPException(status_code=503, detail="Database not configured")
    return next(_get_db())


@router.post("/whatsapp/webhook")
async def whatsapp_webhook(request: Dict[str, Any], authorization: str | None = Header(default=None)):
    # 1. Authorization check
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized")
    token = authorization.split(" ")[1]
    if token != settings.SECRET_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")

    sender = request.get("sender")
    text = request.get("text")
    if not sender or not text:
        raise HTTPException(status_code=400, detail="sender and text are required")

    text_lower = text.strip().lower()
    db = _open_db()

    try:
        # Handle manual reset/restart command
        if text_lower in ("start", "start new survey", "reset", "restart", "hi", "hello"):
            # Deactivate any active/initializing sessions for this user to start fresh
            all_sessions = db.query(IntelligenceSession).filter(
                IntelligenceSession.status.in_(["active", "whatsapp_init"])
            ).all()
            for s in all_sessions:
                if s.payload and s.payload.get("whatsapp_sender") == sender:
                    s.status = "abandoned"
            db.commit()

            # Create fresh init session
            init_session = IntelligenceSession(
                survey_id="emp-2026",
                status="whatsapp_init",
                payload={"whatsapp_sender": sender, "step": "login"}
            )
            db.add(init_session)
            db.commit()

            reply = (
                "🤖 *Welcome to SATARK AI, MoSPI's NSS Survey Assistant.* 🇮🇳\n\n"
                "Please reply with your Enumerator ID (e.g., *ENUM-A* or *ENUM-B*) to view your assigned surveys."
            )
            return {"reply": reply}

        # Check for active or initializing session
        all_sessions = db.query(IntelligenceSession).filter(
            IntelligenceSession.status.in_(["active", "whatsapp_init"])
        ).all()

        active_session = None
        init_session = None
        for s in all_sessions:
            if s.payload and s.payload.get("whatsapp_sender") == sender:
                if s.status == "active":
                    active_session = s
                elif s.status == "whatsapp_init":
                    init_session = s
                break

        # If no session found and not a trigger command, guide user
        if not active_session and not init_session:
            init_session = IntelligenceSession(
                survey_id="emp-2026",
                status="whatsapp_init",
                payload={"whatsapp_sender": sender, "step": "login"}
            )
            db.add(init_session)
            db.commit()
            reply = (
                "🤖 *Welcome to SATARK AI, MoSPI's NSS Survey Assistant.* 🇮🇳\n\n"
                "Please reply with your Enumerator ID (e.g., *ENUM-A* or *ENUM-B*) to view your assigned surveys."
            )
            return {"reply": reply}

        # 2. Handle WhatsApp initialization state
        if init_session:
            step = init_session.payload.get("step")
            if step == "login":
                enumerator_id = text.strip().upper()
                enumerator = db.get(EnumeratorProfile, enumerator_id)
                if not enumerator:
                    return {
                        "reply": f"⚠️ Enumerator ID *{enumerator_id}* not found. Please try again with a valid ID (e.g., *ENUM-A* or *ENUM-B*)."
                    }

                # Query assignments for the enumerator
                assignments = db.query(Assignment).filter(
                    Assignment.enumerator_id == enumerator_id,
                    Assignment.status == "assigned"
                ).all()

                if not assignments:
                    init_session.status = "completed"
                    db.commit()
                    return {
                        "reply": f"👤 Welcome, *{enumerator.name}*!\n\nNo active survey assignments were found in the database for your account."
                    }

                # Update state to select assignment
                payload = dict(init_session.payload)
                payload.update({
                    "step": "select_assignment",
                    "enumerator_id": enumerator_id,
                    "assignments": [str(a.id) for a in assignments]
                })
                init_session.payload = payload
                db.commit()

                # Build response listing assignments
                reply_lines = [
                    f"👤 Welcome, *{enumerator.name}*!\n",
                    "You have the following assigned surveys. Please reply with the list number (e.g., *1*) to start:\n"
                ]
                for idx, a in enumerate(assignments, 1):
                    reply_lines.append(f"*{idx}.* Household: *{a.household_id or 'General'}* (Survey ID: `{a.survey_id}`)")
                
                return {"reply": "\n".join(reply_lines)}

            elif step == "select_assignment":
                assignment_ids = init_session.payload.get("assignments", [])
                try:
                    choice = int(text.strip())
                    if choice < 1 or choice > len(assignment_ids):
                        raise ValueError()
                except ValueError:
                    return {
                        "reply": f"⚠️ Invalid option. Please reply with a number between *1* and *{len(assignment_ids)}*."
                    }

                selected_assignment_id = assignment_ids[choice - 1]

                # Start collection session
                started = start_session(db, {"assignmentId": selected_assignment_id})
                session_id = started["sessionId"]

                # Mark init session completed
                init_session.status = "completed"

                # Update the new active survey session payload with sender details
                new_session = db.get(IntelligenceSession, session_id)
                new_payload = dict(new_session.payload)
                new_payload.update({
                    "whatsapp_sender": sender,
                    "current_question_id": started["currentQuestion"]["id"]
                })
                new_session.payload = new_payload
                db.commit()

                q_msg = _format_question_message(started["currentQuestion"])
                reply = (
                    f"Hello! I'm *SATARK AI*, your NSS Survey Assistant from MoSPI. 🇮🇳\n\n"
                    f"This is a *Household Employment Survey* - takes about 2 minutes.\n\n"
                    f"{q_msg}"
                )
                return {"reply": reply}

        # 3. Handle active survey state
        if active_session:
            current_qid = active_session.payload.get("current_question_id")

            # Submit answer
            res = answer_session(
                db,
                active_session.id,
                {
                    "questionId": current_qid,
                    "value": text.strip(),
                    "elapsedSeconds": 5.0
                }
            )

            # Check for validation failures
            failed_layer = None
            for layer in res.get("intelligence", {}).get("layers", []):
                if layer.get("status") in ("fail", "error"):
                    failed_layer = layer
                    break

            if failed_layer:
                reason = failed_layer.get("reason")
                # Check for age constraint friendly mapping
                if current_qid == "age":
                    reply = "Respondent must be 18 or older Please try again."
                else:
                    reply = f"⚠️ {reason} Please try again."
                return {"reply": reply}

            # Check if survey complete
            if res.get("complete") or not res.get("nextQuestionId"):
                complete_session(db, active_session.id)

                active_session.status = "completed"
                db.commit()

                reply = (
                    "Survey submitted successfully\n\n"
                    "Start New Survey"
                )
                return {"reply": reply}

            # Advance to the next question
            next_q = res["currentQuestion"]
            next_qid = res["nextQuestionId"]

            # Update database session with the next question
            payload = dict(active_session.payload)
            payload["current_question_id"] = next_qid
            active_session.payload = payload
            db.commit()

            q_msg = _format_question_message(next_q)

            # Custom behavior or ordering prefix from intelligence layer
            intel = res.get("intelligence", {})
            prefix = ""
            if intel.get("decision") == "SIMPLIFY":
                prefix = "*[Simplified Language Interface active]:* "
            elif intel.get("decision") == "REORDER":
                prefix = "*[Adaptive Reordering active]:* "

            return {"reply": f"{prefix}{q_msg}"}

    except Exception as e:
        logger.error(f"Error in whatsapp webhook: {e}", exc_info=True)
        return {"reply": "⚠️ An internal error occurred in the SATARK backend. Please try again."}
    finally:
        db.close()


def _format_question_message(question_node: dict) -> str:
    q_text = question_node["q"].get("en", question_node["id"])
    options = question_node.get("options")
    if options and isinstance(options, list):
        q_text += "\n\nOptions:\n" + "\n".join(f"- {opt}" for opt in options)
    return q_text
