"""Document ingest: chunk text/markdown/PDF -> upsert into a bucket."""

from __future__ import annotations

import hashlib
import io
import logging
import re
from typing import Dict, List, Tuple
from uuid import uuid4

from app.intelligence.assist.rag.store import upsert_chunks

logger = logging.getLogger(__name__)


def ingest_bytes(
    bucket: str,
    filename: str,
    data: bytes,
    mime_type: str | None = None,
    metadata: Dict | None = None,
) -> Dict:
    """Ingest a file's bytes into a bucket. Returns counts + source_id."""
    text = _decode(data, filename=filename, mime_type=mime_type)
    chunks = chunk_text(text)
    source_id = uuid4().hex[:12]
    sha256 = hashlib.sha256(data).hexdigest()
    base_meta = {
        "filename": filename,
        "source_id": source_id,
        "sha256": sha256,
        **(metadata or {}),
    }
    metadatas = [{**base_meta, "chunk_index": i} for i in range(len(chunks))]
    ids = [f"{source_id}-{i}" for i in range(len(chunks))]
    written = upsert_chunks(bucket, chunks, metadatas=metadatas, ids=ids, source_id=source_id)
    return {
        "source_id": source_id,
        "filename": filename,
        "bucket": bucket,
        "sha256": sha256,
        "byte_size": len(data),
        "chunk_count": written,
    }


def chunk_text(text: str, max_chars: int = 1200, overlap: int = 200) -> List[str]:
    """Naive paragraph-aware chunker. Splits on blank lines, then merges to ~max_chars."""
    text = (text or "").strip()
    if not text:
        return []
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]

    chunks: List[str] = []
    current = ""
    for paragraph in paragraphs:
        if not current:
            current = paragraph
            continue
        if len(current) + 1 + len(paragraph) <= max_chars:
            current = f"{current}\n\n{paragraph}"
        else:
            chunks.append(current)
            if overlap and len(current) > overlap:
                tail = current[-overlap:]
                current = f"{tail}\n\n{paragraph}"
            else:
                current = paragraph
    if current:
        chunks.append(current)
    return chunks


def _decode(data: bytes, filename: str, mime_type: str | None) -> str:
    name = (filename or "").lower()
    if name.endswith(".pdf") or (mime_type and "pdf" in mime_type.lower()):
        return _pdf_to_text(data)
    # text / markdown / unknown
    for encoding in ("utf-8", "utf-16", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("latin-1", errors="ignore")


def _pdf_to_text(data: bytes) -> str:
    try:
        import pypdf  # type: ignore

        reader = pypdf.PdfReader(io.BytesIO(data))
        pages = []
        for page in reader.pages:
            try:
                pages.append(page.extract_text() or "")
            except Exception:  # noqa: BLE001
                continue
        return "\n\n".join(pages)
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"PDF parsing failed; install/repair pypdf support: {exc}") from exc
