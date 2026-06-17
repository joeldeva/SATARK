import copy
import logging
import re
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class RAGEngine:
    """
    Question retrieval for the deterministic survey engine.
    Uses explainable local keyword ranking only; no model downloads or external
    embedding services are allowed in offline mode.
    """

    def __init__(self, knowledge_base_loader):
        self.kb = knowledge_base_loader
        logger.info("RAG local keyword mode enabled")

    def build_index(self):
        return self

    def search(self, query: str, domain: Optional[str] = None, tags: Optional[List[str]] = None, top_k: int = 20) -> List[Dict]:
        bundled = self._keyword_search(query, domain, tags or [], top_k)
        uploaded = self._uploaded_question_search(query, domain, tags or [], top_k)
        return self._dedupe([*uploaded, *bundled])[:top_k]

    def _keyword_search(self, query: str, domain: Optional[str], tags: List[str], top_k: int) -> List[Dict]:
        query_words = self._tokens(query)
        tag_words = {tag.lower() for tag in tags}
        candidates = []

        for question in self._candidate_questions(domain):
            question_words = self._tokens(self._question_text(question))
            question_tags = {tag.lower() for tag in question.get("tags", [])}
            score = 0

            score += len(query_words & question_words) * 3
            score += len(tag_words & question_tags) * 4
            if domain and question.get("domain") == domain:
                score += 4
            if question.get("category") == "core":
                score += 2
            if question.get("category") == "screening":
                score += 2
            if question.get("source"):
                score += 1

            if score > 0:
                ranked = copy.deepcopy(question)
                ranked["relevance_score"] = score
                candidates.append(ranked)

        if not candidates:
            candidates = [copy.deepcopy(q) for q in self._candidate_questions(domain)]
            for question in candidates:
                question["relevance_score"] = 0

        candidates.sort(key=lambda item: item.get("relevance_score", 0), reverse=True)
        return candidates[:top_k]

    def _candidate_questions(self, domain: Optional[str]) -> List[Dict]:
        if not domain:
            return self.kb.get_all_questions()
        domain = "labour" if domain == "employment" else domain
        questions = self.kb.get_questions_by_domain(domain)
        questions.extend(self.kb.get_questions_by_domain("household"))
        return questions

    def _question_text(self, question: Dict) -> str:
        parts = [
            question.get("text", ""),
            question.get("domain", ""),
            question.get("category", ""),
            " ".join(question.get("tags", [])),
            question.get("standard_code") or "",
        ]
        return " ".join(part for part in parts if part)

    def _tokens(self, value: str) -> set[str]:
        return set(re.findall(r"\b[a-z0-9_]{3,}\b", value.lower()))

    def _uploaded_question_search(self, query: str, domain: Optional[str], tags: List[str], top_k: int) -> List[Dict]:
        """Use indexed SDRD question banks as generation candidates.

        This is an assist-lane dependency. If the vector store is unavailable,
        generation still works from bundled standards and deterministic rules.
        """
        try:
            from app.intelligence.assist.rag.store import query as store_query

            hits = store_query("survey_generation", " ".join([query or "", domain or "", " ".join(tags)]), k=max(top_k, 10))
        except Exception as exc:  # noqa: BLE001
            logger.info("Uploaded source retrieval unavailable for generation: %s", exc)
            return []

        questions: List[Dict] = []
        for idx, hit in enumerate(hits):
            text = self._question_from_chunk(hit.get("text") or "")
            if not text:
                continue
            meta = hit.get("metadata") or {}
            qid = meta.get("question_id") or f"rag_{idx + 1}"
            options = self._options_from_meta(meta)
            question_type = "single_choice" if options else self._infer_type(text, meta)
            questions.append({
                "id": str(qid).lower().replace(" ", "_").replace(".", "_"),
                "domain": domain or "general",
                "subdomain": str(meta.get("section") or "uploaded_question_bank").lower().replace(" ", "_"),
                "text": text,
                "type": question_type,
                "category": "core",
                "tags": list({*(tags or []), "uploaded_source", "rag"}),
                "options": options,
                "validation": self._validation_from_meta(meta),
                "required": True,
                "routing": meta.get("skip_logic"),
                "standard_code": meta.get("code_type"),
                "source": meta.get("source_document") or meta.get("filename") or "uploaded_question_bank",
                "source_trace": {
                    "source_document": meta.get("source_document") or meta.get("filename") or "Uploaded Question Bank",
                    "section": meta.get("section") or "Question bank",
                    "question_id": meta.get("question_id") or qid,
                    "language": meta.get("language") or "English",
                    "confidence": round(float(hit.get("score") or 0.0) * 100),
                    "retrieved_context": (hit.get("text") or "")[:500],
                    "generated_reason": "Matched the survey goal through hybrid retrieval and reranking.",
                },
                "relevance_score": round(float(hit.get("score") or 0.0) * 100),
            })
        return questions

    def _question_from_chunk(self, chunk: str) -> str:
        lines = [line.strip() for line in (chunk or "").splitlines() if line.strip()]
        if not lines:
            return ""
        for line in lines:
            cleaned = re.sub(r"^\s*(?:q(?:uestion)?[ _.-]*\d+[a-z]?|[a-z]{2,8}[_-]\d{1,4}|[0-9]{1,3}[.)])\s*[:.-]?\s*", "", line, flags=re.I)
            if "?" in cleaned or len(cleaned.split()) >= 5:
                return cleaned.strip()
        return lines[0]

    def _options_from_meta(self, meta: Dict) -> List[Dict]:
        raw = meta.get("options")
        if not raw:
            return []
        if isinstance(raw, list):
            values = [str(item).strip() for item in raw if str(item).strip()]
        else:
            values = [part.strip(" -;") for part in re.split(r"[,/|;]", str(raw)) if part.strip(" -;")]
        return [{"value": value.lower().replace(" ", "_"), "label": value} for value in values[:12]]

    def _validation_from_meta(self, meta: Dict) -> Dict:
        raw = str(meta.get("validation") or "")
        if not raw:
            return {}
        numbers = [float(value) for value in re.findall(r"-?\d+(?:\.\d+)?", raw)]
        if len(numbers) >= 2:
            return {"type": "range", "min": numbers[0], "max": numbers[1]}
        if "mandatory" in raw.lower() or "required" in raw.lower():
            return {"type": "required"}
        return {"note": raw}

    def _infer_type(self, text: str, meta: Dict) -> str:
        haystack = " ".join([text, str(meta.get("validation") or "")]).lower()
        if any(word in haystack for word in ["how many", "how much", "amount", "income", "age", "number"]):
            return "number"
        if any(word in haystack for word in ["date", "when"]):
            return "date"
        return "text"

    def _dedupe(self, questions: List[Dict]) -> List[Dict]:
        seen: set[str] = set()
        out: List[Dict] = []
        for question in questions:
            key = re.sub(r"\s+", " ", self._question_text(question).lower()).strip()
            if not key or key in seen:
                continue
            seen.add(key)
            out.append(question)
        return out
