"""Document ingest: chunk text/markdown/PDF -> upsert into a bucket."""

from __future__ import annotations

import hashlib
import io
import logging
import re
import zipfile
import xml.etree.ElementTree as ET
from typing import Any, Dict, List
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
    chunk_records = chunk_question_blocks(text)
    chunks = [record["text"] for record in chunk_records]
    source_id = uuid4().hex[:12]
    sha256 = hashlib.sha256(data).hexdigest()
    base_meta = {
        "filename": filename,
        "source_id": source_id,
        "sha256": sha256,
        **(metadata or {}),
    }
    metadatas = [
        {
            **base_meta,
            **(record.get("metadata") or {}),
            "chunk_index": i,
        }
        for i, record in enumerate(chunk_records)
    ]
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


def chunk_question_blocks(text: str, max_chars: int = 1600) -> List[Dict[str, Any]]:
    """Question-aware chunking for QBS/DDI/codebook uploads.

    A fixed-size chunk can split a question from its options, validation notes,
    and skip instructions. For survey generation, that is exactly the wrong
    boundary. This parser keeps one survey question block together whenever it
    can detect question markers, and falls back to paragraph chunks for ordinary
    documents.
    """
    text = (text or "").strip()
    if not text:
        return []

    lines = [line.rstrip() for line in text.splitlines()]
    source_meta = _document_metadata(lines)
    starts = []
    question_start = re.compile(
        r"^\s*(?:q(?:uestion)?[ _.-]*\d+[a-z]?|[a-z]{2,8}[_-]\d{1,4}|[0-9]{1,3}[.)])\b",
        re.IGNORECASE,
    )
    for idx, line in enumerate(lines):
        if question_start.search(line):
            starts.append(idx)

    if not starts:
        return [
            {"text": chunk, "metadata": {**source_meta, "chunk_type": "paragraph"}}
            for chunk in chunk_text(text)
        ]

    starts.append(len(lines))
    records: List[Dict[str, Any]] = []
    for pos in range(len(starts) - 1):
        block_lines = lines[starts[pos] : starts[pos + 1]]
        block = "\n".join(line for line in block_lines if line.strip()).strip()
        if not block:
            continue
        if len(block) > max_chars:
            # Preserve the question stem in each overflow chunk.
            stem = block_lines[0].strip()
            for idx, part in enumerate(chunk_text(block, max_chars=max_chars, overlap=120)):
                records.append({
                    "text": part if idx == 0 else f"{stem}\n{part}",
                    "metadata": {
                        **source_meta,
                        **_question_metadata(block),
                        "chunk_type": "question_block_part",
                        "block_part": idx,
                    },
                })
            continue
        records.append({
            "text": block,
            "metadata": {
                **source_meta,
                **_question_metadata(block),
                "chunk_type": "question_block",
            },
        })
    return records or [{"text": chunk, "metadata": {**source_meta, "chunk_type": "paragraph"}} for chunk in chunk_text(text)]


def _document_metadata(lines: List[str]) -> Dict[str, str]:
    header = "\n".join(lines[:30])
    filename_style = re.search(r"\b(PLFS|HCES|NSS|ASUSE|AGCENSUS|ECONCENSUS)[ _-]?([0-9]{2,4}(?:[-_][0-9]{2,4})?)?\b", header, re.I)
    section = re.search(r"\bSection\s*[:.-]?\s*([A-Za-z0-9 ._-]{2,80})", header, re.I)
    language = re.search(r"\bLanguage\s*[:.-]?\s*([A-Za-z ]{2,40})", header, re.I)
    meta: Dict[str, str] = {}
    if filename_style:
        survey = filename_style.group(1).upper()
        year = (filename_style.group(2) or "").replace("_", "-")
        meta["source_document"] = f"{survey} {year}".strip()
    if section:
        meta["section"] = section.group(1).strip()
    if language:
        meta["language"] = language.group(1).strip()
    return meta


def _question_metadata(block: str) -> Dict[str, Any]:
    first = next((line.strip() for line in block.splitlines() if line.strip()), "")
    qid_match = re.match(r"^\s*([A-Za-z]{0,10}[ _.-]?\d{1,4}[A-Za-z]?|[0-9]{1,3})", first)
    section = re.search(r"\bSection\s*[:.-]?\s*([A-Za-z0-9 ._-]{2,80})", block, re.I)
    options = re.findall(r"(?:^|\n)\s*(?:Option[s]?|Choices?)\s*[:.-]\s*([^\n]+)", block, re.I)
    validation = re.search(r"\b(?:Validation|Rule|Range)\s*[:.-]\s*([^\n]+)", block, re.I)
    skip = re.search(r"\b(?:Skip|Go to|If .* then)\s*[:.-]?\s*([^\n]+)", block, re.I)
    meta: Dict[str, Any] = {}
    if qid_match:
        meta["question_id"] = qid_match.group(1).replace(" ", "_").replace(".", "_")
    if section:
        meta["section"] = section.group(1).strip()
    if options:
        meta["options"] = options[0].strip()
    if validation:
        meta["validation"] = validation.group(1).strip()
    if skip:
        meta["skip_logic"] = skip.group(1).strip()
    return meta


def _decode(data: bytes, filename: str, mime_type: str | None) -> str:
    name = (filename or "").lower()
    if name.endswith(".pdf") or (mime_type and "pdf" in mime_type.lower()):
        return _pdf_to_text(data)
    if name.endswith(".docx") or (mime_type and "wordprocessingml" in mime_type.lower()):
        return _docx_to_text(data)
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


def _docx_to_text(data: bytes) -> str:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            xml = archive.read("word/document.xml")
        root = ET.fromstring(xml)
        namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        paragraphs = []
        for paragraph in root.findall(".//w:p", namespace):
            text = "".join(node.text or "" for node in paragraph.findall(".//w:t", namespace)).strip()
            if text:
                paragraphs.append(text)
        return "\n\n".join(paragraphs)
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"DOCX parsing failed; upload a valid .docx file: {exc}") from exc
