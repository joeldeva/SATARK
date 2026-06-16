"""Embedding provider for the assist RAG lane.

Production target is the neural sentence model
``paraphrase-multilingual-MiniLM-L12-v2`` (set ``RAG_EMBEDDINGS=st`` once the
model is available locally).  When the model is not present — offline demo box,
CI — we fall back to a deterministic, dependency-free *lexical-semantic*
embedding that still captures real semantic overlap via:

  • word stemming        (monthly → month, spending → spend)
  • a curated synonym map (spending/expenses → expenditure, salary → income)
  • character 4-grams     (fuzzy overlap: expenditure ↔ expenditur)

This keeps RAG retrieval working without network access while remaining a true
vector space (cosine similarity), and swaps transparently to the neural model
in production.  This module lives in the assist lane only — never imported by
the verdict lane.
"""
from __future__ import annotations

import hashlib
import logging
import math
import os
import re
from typing import List

logger = logging.getLogger(__name__)

DIMENSIONS = 512

# Canonical-form synonym map for common survey / economic vocabulary so that
# lexically different but semantically close terms collide in vector space.
_SYNONYMS = {
    "spending": "expenditure", "spend": "expenditure", "spends": "expenditure",
    "spent": "expenditure", "expense": "expenditure", "expenses": "expenditure",
    "expenditure": "expenditure", "cost": "expenditure", "costs": "expenditure",
    "outlay": "expenditure", "consumption": "expenditure",
    "income": "income", "earning": "income", "earnings": "income", "earn": "income",
    "salary": "income", "salaried": "income", "wage": "income", "wages": "income",
    "revenue": "income", "pay": "income", "remuneration": "income",
    "monthly": "month", "month": "month", "months": "month",
    "annual": "year", "annually": "year", "yearly": "year", "year": "year",
    "occupation": "occupation", "job": "occupation", "profession": "occupation",
    "employment": "occupation", "employed": "occupation", "work": "occupation",
    "household": "household", "family": "household", "home": "household",
    "house": "household", "domestic": "household",
    "fishery": "fishery", "fisheries": "fishery", "fishing": "fishery", "fish": "fishery",
    "fisherman": "fishery", "fishers": "fishery",
    "agriculture": "agriculture", "farming": "agriculture", "farm": "agriculture",
    "farmer": "agriculture", "crop": "agriculture", "cultivation": "agriculture",
    "education": "education", "school": "education", "literacy": "education",
    "health": "health", "medical": "health", "illness": "health",
}

_SUFFIXES = (" ", "ing", "ment", "tion", "sion", "ance", "ence", "ness", "ly", "ed", "es", "s")


def _stem(token: str) -> str:
    for suffix in _SUFFIXES:
        if suffix.strip() and len(token) > len(suffix) + 2 and token.endswith(suffix):
            return token[: -len(suffix)]
    return token


def _features(text: str) -> List[str]:
    text = (text or "").lower()
    tokens = re.findall(r"\b[\w]{2,}\b", text)
    features: List[str] = []
    for token in tokens:
        features.append(f"w:{token}")
        stem = _stem(token)
        if stem != token:
            features.append(f"w:{stem}")
        canon = _SYNONYMS.get(token) or _SYNONYMS.get(stem)
        if canon:
            features.append(f"c:{canon}")
    # character 4-grams over the alphanumeric stream for fuzzy overlap
    stream = re.sub(r"[^a-z0-9]+", "", text)
    for i in range(0, max(0, len(stream) - 3)):
        features.append(f"g:{stream[i:i + 4]}")
    return features


def _hash_embed(text: str, dimensions: int = DIMENSIONS) -> List[float]:
    vector = [0.0] * dimensions
    for feature in _features(text):
        digest = hashlib.sha256(feature.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % dimensions
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        # weight canonical-synonym features higher so semantic matches dominate
        weight = 2.5 if feature.startswith("c:") else (1.4 if feature.startswith("w:") else 0.6)
        vector[index] += sign * weight
    norm = math.sqrt(sum(value * value for value in vector))
    if not norm:
        return vector
    return [round(value / norm, 6) for value in vector]


# ── optional neural backend ───────────────────────────────────────────────
_ST_MODEL = None


def _try_sentence_transformer():
    global _ST_MODEL
    if _ST_MODEL is not None:
        return _ST_MODEL
    if os.getenv("RAG_EMBEDDINGS", "local").lower() != "st":
        return None
    try:
        from sentence_transformers import SentenceTransformer  # noqa: PLC0415

        _ST_MODEL = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
        logger.info("RAG embeddings: using neural model paraphrase-multilingual-MiniLM-L12-v2")
        return _ST_MODEL
    except Exception as exc:  # noqa: BLE001
        logger.warning("Neural embedding model unavailable, using local embedding: %s", exc)
        return None


def embed(texts: List[str]) -> List[List[float]]:
    """Embed a batch of texts. Neural model if configured/available, else local."""
    model = _try_sentence_transformer()
    if model is not None:
        return [list(map(float, vec)) for vec in model.encode(list(texts), normalize_embeddings=True)]
    return [_hash_embed(text) for text in texts]


def embed_one(text: str) -> List[float]:
    return embed([text])[0]


def backend() -> str:
    return "sentence-transformer" if _try_sentence_transformer() is not None else "local-lexical"
