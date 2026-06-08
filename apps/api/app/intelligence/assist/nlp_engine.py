from __future__ import annotations

import re


_DEVANAGARI = re.compile(r"[\u0900-\u097F]")
_TAMIL = re.compile(r"[\u0B80-\u0BFF]")


def detect_language(text: str) -> str:
    if _TAMIL.search(text):
        return "ta"
    if _DEVANAGARI.search(text):
        return "hi"
    return "en"


def extract_text_features(text: str, hint: str | None = None) -> dict:
    normalized = re.sub(r"\s+", " ", text.strip().lower())
    occupation_cues = ("driver", "farmer", "teacher", "developer", "worker", "shop", "engineer")
    intent = hint or ("occupation" if any(cue in normalized for cue in occupation_cues) else "generic")
    return {
        "raw": text,
        "normalized": normalized,
        "language": detect_language(text),
        "intent": intent,
        "entities": [{"type": "occupation", "text": cue} for cue in occupation_cues if cue in normalized],
        "needs_review": True,
        "is_verdict": False,
    }
