"""Load questionnaire volume JSON files into first-class RAG buckets.

Run from the apps/api directory:
    python scripts/load_volume_rag_buckets.py

Idempotent: each configured volume source is deleted by stable source_id and
then reloaded from the current JSON file contents.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
import sys
from pathlib import Path
from typing import Any

# Ensure apps/api is on the path for app imports.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.intelligence.assist.rag.store import delete_source_chunks, upsert_chunks

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
VOLUME_SOURCES = {
    "volume_1": PROJECT_ROOT / "database" / "volume1" / "questions1.json",
    "volume_2": PROJECT_ROOT / "database" / "Volume2" / "questions.json",
}


def _safe_id(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip())
    return value.strip("_") or "record"


def _load_records(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, list):
        raise ValueError(f"{path} must contain a JSON list")

    records: list[dict[str, Any]] = []
    for index, item in enumerate(data):
        if not isinstance(item, dict):
            logger.warning("Skipping non-object record %s in %s", index, path)
            continue
        question_id = str(item.get("question_id") or "").strip()
        content = str(item.get("content") or "").strip()
        if not question_id or not content:
            logger.warning("Skipping blank record %s in %s", index, path)
            continue
        records.append({"question_id": question_id, "content": content})
    return records


def load_volume(bucket: str, path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Volume JSON not found: {path}")

    raw = path.read_bytes()
    sha256 = hashlib.sha256(raw).hexdigest()
    records = _load_records(path)
    source_id = f"{bucket}:{path.name}"
    source_document = bucket.replace("_", " ").title()

    chunks = [f"{record['question_id']}\n{record['content']}" for record in records]
    metadatas = [
        {
            "source_id": source_id,
            "source_document": source_document,
            "source_type": "volume_question_json",
            "filename": path.name,
            "path": str(path.relative_to(PROJECT_ROOT)),
            "sha256": sha256,
            "chunk_index": index,
            "chunk_type": "question_record",
            "question_id": record["question_id"],
        }
        for index, record in enumerate(records)
    ]
    ids = [
        f"{_safe_id(source_id)}-{index:05d}-{_safe_id(record['question_id'])}"
        for index, record in enumerate(records)
    ]

    deleted = delete_source_chunks(bucket, source_id)
    written = upsert_chunks(bucket, chunks, metadatas=metadatas, ids=ids, source_id=source_id)
    return {
        "bucket": bucket,
        "source_id": source_id,
        "path": str(path),
        "sha256": sha256,
        "records": len(records),
        "deleted": deleted,
        "written": written,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Load volume_1 and volume_2 RAG buckets from JSON files.")
    parser.add_argument(
        "--bucket",
        choices=sorted(VOLUME_SOURCES),
        help="Load only one bucket. Defaults to all configured volume buckets.",
    )
    args = parser.parse_args()

    selected = {args.bucket: VOLUME_SOURCES[args.bucket]} if args.bucket else VOLUME_SOURCES
    try:
        for bucket, path in selected.items():
            result = load_volume(bucket, path)
            logger.info(
                "%s loaded: %d records written, %d previous chunks deleted (%s)",
                result["bucket"],
                result["written"],
                result["deleted"],
                result["source_id"],
            )
    except Exception:
        logger.exception("Failed to load volume RAG buckets")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
