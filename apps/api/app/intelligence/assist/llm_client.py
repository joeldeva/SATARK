"""Assist-lane LLM client (OpenRouter / Ollama).

Used ONLY in the assist lane (RAG grounded answers, suggestions). Never imported
by the verdict lane. Returns None when no LLM is configured so callers fall back
to deterministic behaviour — the assist lane must degrade, never crash.
"""
from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request

from app.config import settings

logger = logging.getLogger(__name__)


def available() -> bool:
    provider = (settings.LLM_PROVIDER or "none").lower()
    if provider == "openrouter":
        return bool(settings.OPENROUTER_API_KEY)
    return provider == "ollama"


def chat(messages: list[dict], temperature: float = 0.2, max_tokens: int = 600) -> str | None:
    """Single-shot chat completion. Returns the text, or None on any failure."""
    provider = (settings.LLM_PROVIDER or "none").lower()
    try:
        if provider == "openrouter" and settings.OPENROUTER_API_KEY:
            return _openrouter(messages, temperature, max_tokens)
        if provider == "ollama":
            return _ollama(messages, temperature)
    except Exception as exc:  # noqa: BLE001 — assist must degrade gracefully
        logger.warning("Assist LLM call failed (%s): %s", provider, exc)
    return None


def _openrouter(messages, temperature, max_tokens) -> str:
    body = json.dumps({
        "model": settings.OPENROUTER_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{settings.OPENROUTER_BASE_URL.rstrip('/')}/chat/completions",
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
            "HTTP-Referer": "https://satark.gov.in",
            "X-Title": "SATARK Survey Intelligence",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=settings.LLM_TIMEOUT_SECONDS) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return str((data.get("choices") or [{}])[0].get("message", {}).get("content", "")).strip()


def _ollama(messages, temperature) -> str:
    body = json.dumps({
        "model": settings.LLM_MODEL,
        "stream": False,
        "options": {"temperature": temperature},
        "messages": messages,
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/chat",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=settings.LLM_TIMEOUT_SECONDS) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return str(data.get("message", {}).get("content", "")).strip()
