from typing import List, Dict
import logging
import json

logger = logging.getLogger(__name__)


class RAGEngine:
    """
    Retrieval engine for finding relevant survey questions.
    Uses SentenceTransformers + ChromaDB when available,
    falls back to keyword search for offline/lightweight mode.
    """

    def __init__(self, knowledge_base_loader):
        self.kb = knowledge_base_loader
        self.collection = None
        self._use_vector = False

        try:
            from sentence_transformers import SentenceTransformer
            import chromadb

            self.model = SentenceTransformer('all-MiniLM-L6-v2')
            self.client = chromadb.Client()
            self._use_vector = True
            logger.info("✅ RAG: Vector mode (SentenceTransformers + ChromaDB)")
        except Exception as e:
            logger.warning(f"⚠️  RAG: Falling back to keyword search ({e})")

    def build_index(self):
        if not self._use_vector:
            logger.info("✅ RAG: Keyword index ready (no vector DB needed)")
            return self

        try:
            try:
                self.collection = self.client.get_collection("satark_questions")
                logger.info("✅ Using existing ChromaDB collection")
                return self
            except Exception:
                self.collection = self.client.create_collection("satark_questions")

            documents, metadatas, ids = [], [], []

            for domain, survey_data in self.kb.surveys.items():
                for q in survey_data.get("questions", []):
                    text = f"{q['text']} {' '.join(q.get('tags', []))} {q.get('category', '')}"
                    documents.append(text)
                    metadatas.append({
                        "domain": domain,
                        "question_id": q["id"],
                        "type": q["type"],
                        "category": q.get("category", ""),
                        "tags": ",".join(q.get("tags", [])),
                        "raw": json.dumps(q)
                    })
                    ids.append(f"{domain}_{q['id']}")

            if documents:
                batch_size = 100
                for i in range(0, len(documents), batch_size):
                    self.collection.add(
                        documents=documents[i:i+batch_size],
                        metadatas=metadatas[i:i+batch_size],
                        ids=ids[i:i+batch_size]
                    )
                logger.info(f"✅ Indexed {len(documents)} questions")
        except Exception as e:
            logger.error(f"❌ Index build failed: {e}")
            self._use_vector = False

        return self

    def search(self, query: str, domain: str = None, tags: List[str] = None, top_k: int = 20) -> List[Dict]:
        if self._use_vector and self.collection:
            return self._vector_search(query, domain, tags, top_k)
        return self._keyword_search(query, domain, tags, top_k)

    def _vector_search(self, query: str, domain: str, tags: List[str], top_k: int) -> List[Dict]:
        try:
            where = {"domain": domain} if domain else None
            results = self.collection.query(query_texts=[query], n_results=top_k, where=where)
            questions = []
            if results and results['metadatas']:
                for i, meta in enumerate(results['metadatas'][0]):
                    q = json.loads(meta['raw'])
                    q['relevance_score'] = 1 - results['distances'][0][i]
                    questions.append(q)
            if tags:
                questions = [q for q in questions if any(t in q.get('tags', []) for t in tags)]
            return questions
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return self._keyword_search(query, domain, tags, top_k)

    def _keyword_search(self, query: str, domain: str, tags: List[str], top_k: int) -> List[Dict]:
        query_words = set(query.lower().split())
        results = []

        search_domains = [domain] if domain else list(self.kb.surveys.keys())
        for d in search_domains:
            for q in self.kb.surveys.get(d, {}).get("questions", []):
                score = 0
                q_text = q.get("text", "").lower()
                q_tags = set(q.get("tags", []))

                # Score by keyword overlap
                score += len(query_words & set(q_text.split()))
                if tags:
                    score += len(set(tags) & q_tags) * 2

                if score > 0:
                    q['relevance_score'] = score
                    results.append(q)

        results.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
        return results[:top_k]
