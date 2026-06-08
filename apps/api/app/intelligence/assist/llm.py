from __future__ import annotations

import json
import urllib.request

from app.config import settings


def generate(prompt: str, context: str | None = None, max_tokens: int = 512) -> dict:
    body = {
        "model": settings.gemma_model,
        "prompt": f"{prompt}\n\nContext:\n{context}" if context else prompt,
        "stream": False,
        "options": {"num_predict": max_tokens, "temperature": 0.2},
    }
    data = json.dumps(body).encode("utf-8")
    request = urllib.request.Request(
        f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/generate",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=settings.LLM_TIMEOUT_SECONDS) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return {
        "text": payload.get("response", ""),
        "model": settings.gemma_model,
        "provider": "ollama",
        "needs_review": True,
        "is_verdict": False,
    }
