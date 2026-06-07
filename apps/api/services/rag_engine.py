import copy
import json
import logging
import re
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class RAGEngine:
    """
    Question retrieval for the deterministic survey engine.
    Uses vector search when optional dependencies are installed and falls back
    to explainable keyword ranking.
    """

    def __init__(self, knowledge_base_loader):
        self.kb = knowledge_base_loader
        self.collection = None
        self._use_vector = False

        try:
            from sentence_transformers import SentenceTransformer
            import chromadb

            self.model = SentenceTransformer("all-MiniLM-L6-v2")
            self.client = chromadb.Client()
            self._use_vector = True
            logger.info("RAG vector mode enabled")
        except Exception as exc:
            logger.info("RAG keyword mode enabled: %s", exc)

    def build_index(self):
        if not self._use_vector:
            return self

        try:
            try:
                self.collection = self.client.get_collection("satark_questions")
                return self
            except Exception:
                self.collection = self.client.create_collection("satark_questions")

            documents, metadatas, ids = [], [], []
            for question in self.kb.get_all_questions():
                documents.append(self._question_text(question))
                metadatas.append({
                    "domain": question.get("domain"),
                    "question_id": question["id"],
                    "raw": json.dumps(question),
                })
                ids.append(question["id"])

            if documents:
                self.collection.add(documents=documents, metadatas=metadatas, ids=ids)
        except Exception as exc:
            logger.warning("Vector index unavailable, falling back to keyword mode: %s", exc)
            self._use_vector = False

        return self

    def search(self, query: str, domain: Optional[str] = None, tags: Optional[List[str]] = None, top_k: int = 20) -> List[Dict]:
        if self._use_vector and self.collection:
            return self._vector_search(query, domain, tags or [], top_k)
        return self._keyword_search(query, domain, tags or [], top_k)

    def _vector_search(self, query: str, domain: Optional[str], tags: List[str], top_k: int) -> List[Dict]:
        try:
            where = {"domain": domain} if domain else None
            results = self.collection.query(query_texts=[query], n_results=top_k, where=where)
            questions = []
            for index, metadata in enumerate(results.get("metadatas", [[]])[0]):
                question = json.loads(metadata["raw"])
                question["relevance_score"] = 1 - results.get("distances", [[0]])[0][index]
                questions.append(question)
            return questions
        except Exception as exc:
            logger.warning("Vector search failed, using keyword mode: %s", exc)
            return self._keyword_search(query, domain, tags, top_k)

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
