"""
SATARK.AI Retrieval Engine
Embedding-based question retrieval using SentenceTransformers + FAISS
"""

import json
import numpy as np
from typing import List, Dict, Optional
from pathlib import Path
import logging
from sentence_transformers import SentenceTransformer
import faiss

from models.survey_schema import PromptIntent
from config import ML_CONFIG, DATABASE_PATHS

logger = logging.getLogger(__name__)


class RetrievalEngine:
    """
    Semantic question retrieval using embeddings.
    No hallucination - only retrieves existing official questions.
    """
    
    def __init__(self):
        """Initialize the retrieval engine."""
        self.model = None
        self.index = None
        self.questions_db = []
        self.embeddings_path = Path(__file__).parent.parent / "ml" / "embeddings" / "question_vectors.faiss"
        self.metadata_path = Path(__file__).parent.parent / "ml" / "embeddings" / "questions_metadata.json"
        
        self._initialize_engine()
    
    def retrieve_questions(self, intent: PromptIntent, max_questions: int = 20) -> List[Dict]:
        """
        Retrieve relevant questions based on intent.
        Returns official questions from government sources.
        """
        if not self.model or not self.index:
            logger.warning("⚠️ Retrieval engine not available, using fallback")
            return self._fallback_retrieval(intent, max_questions)
        
        try:
            # Create search query from intent
            query = self._create_search_query(intent)
            logger.debug(f"Search query: {query}")
            
            # Get embeddings for query
            query_embedding = self.model.encode([query])
            
            # Search in FAISS index
            scores, indices = self.index.search(
                query_embedding.astype('float32'), 
                min(max_questions * 2, len(self.questions_db))
            )
            
            # Filter and rank results
            results = []
            for score, idx in zip(scores[0], indices[0]):
                if idx < len(self.questions_db) and idx >= 0:
                    question = self.questions_db[idx].copy()
                    question['relevance_score'] = float(score)
                    
                    # Apply filters based on intent
                    if self._matches_intent(question, intent):
                        results.append(question)
            
            # Sort by relevance and domain match
            results = self._rank_questions(results, intent)
            
            logger.info(f"✅ Retrieved {len(results[:max_questions])} relevant questions")
            return results[:max_questions]
            
        except Exception as e:
            logger.error(f"❌ Error in question retrieval: {e}")
            return self._fallback_retrieval(intent, max_questions)
    
    def _initialize_engine(self):
        """Initialize embedding model and vector index."""
        try:
            # Load or create embeddings
            if self.embeddings_path.exists() and self.metadata_path.exists():
                self._load_embeddings()
            else:
                self._create_embeddings()
                
        except Exception as e:
            logger.error(f"❌ Error initializing retrieval engine: {e}")
            self.model = None
            self.index = None
    
    def _load_embeddings(self):
        """Load pre-computed embeddings."""
        try:
            # Load FAISS index
            self.index = faiss.read_index(str(self.embeddings_path))
            
            # Load questions metadata
            with open(self.metadata_path, 'r', encoding='utf-8') as f:
                self.questions_db = json.load(f)
            
            # Load sentence transformer model
            self.model = SentenceTransformer(ML_CONFIG['embedding_model'])
            
            logger.info(f"✅ Loaded {len(self.questions_db)} questions with embeddings")
            
        except Exception as e:
            logger.error(f"❌ Error loading embeddings: {e}")
            self._create_embeddings()
    
    def _create_embeddings(self):
        """Create embeddings from question bank."""
        try:
            logger.info("🔧 Creating question embeddings...")
            
            # Load sentence transformer model
            self.model = SentenceTransformer(ML_CONFIG['embedding_model'])
            
            # Load questions from database
            questions = self._load_questions()
            
            if not questions:
                logger.warning("⚠️ No questions found to create embeddings")
                return
            
            # Create text representations for embedding
            question_texts = []
            for q in questions:
                text = self._create_question_text(q)
                question_texts.append(text)
            
            # Generate embeddings
            embeddings = self.model.encode(question_texts, show_progress_bar=True)
            
            # Create FAISS index
            dimension = embeddings.shape[1]
            self.index = faiss.IndexFlatIP(dimension)  # Inner product for similarity
            
            # Normalize embeddings for cosine similarity
            faiss.normalize_L2(embeddings.astype('float32'))
            self.index.add(embeddings.astype('float32'))
            
            # Save embeddings and metadata
            self.embeddings_path.parent.mkdir(parents=True, exist_ok=True)
            faiss.write_index(self.index, str(self.embeddings_path))
            
            with open(self.metadata_path, 'w', encoding='utf-8') as f:
                json.dump(questions, f, ensure_ascii=False, indent=2)
            
            self.questions_db = questions
            
            logger.info(f"✅ Created embeddings for {len(questions)} questions")
            
        except Exception as e:
            logger.error(f"❌ Error creating embeddings: {e}")
            self.model = None
            self.index = None
    
    def _load_questions(self) -> List[Dict]:
        """Load questions from question bank."""
        questions = []
        
        try:
            # Load from main question bank
            if DATABASE_PATHS['question_bank'].exists():
                with open(DATABASE_PATHS['question_bank'], 'r', encoding='utf-8') as f:
                    questions.extend(json.load(f))
            
            logger.info(f"Loaded {len(questions)} questions from database")
            
        except Exception as e:
            logger.error(f"Error loading questions: {e}")
        
        return questions
    
    def _create_question_text(self, question: Dict) -> str:
        """Create searchable text representation of question."""
        parts = []
        
        # Add question text (English)
        if isinstance(question.get('text'), dict):
            parts.append(question['text'].get('en', ''))
        else:
            parts.append(str(question.get('text', '')))
        
        # Add domain and subdomain
        parts.append(question.get('domain', ''))
        parts.append(question.get('subdomain', ''))
        
        # Add tags
        if question.get('tags'):
            parts.extend(question['tags'])
        
        # Add audience
        if question.get('audience'):
            parts.extend(question['audience'])
        
        # Add category
        parts.append(question.get('category', ''))
        
        return ' '.join(filter(None, parts))
    
    def _create_search_query(self, intent: PromptIntent) -> str:
        """Create search query from intent."""
        parts = []
        
        if intent.domain:
            parts.append(intent.domain)
        
        if intent.topic:
            parts.append(intent.topic)
        
        if intent.audience:
            parts.append(intent.audience)
        
        parts.extend(intent.keywords)
        
        return ' '.join(filter(None, parts))
    
    def _matches_intent(self, question: Dict, intent: PromptIntent) -> bool:
        """Check if question matches the intent."""
        # Always include demographic questions
        if question.get('domain') == 'demographic':
            return True
        
        # Domain match - be more flexible
        if intent.domain:
            question_domain = question.get('domain')
            if question_domain == intent.domain:
                return True
            
            # Allow related domains
            related_domains = {
                'labour': ['household', 'education'],
                'health': ['household'],
                'agriculture': ['household', 'labour'],
                'enterprise': ['labour', 'household'],
                'education': ['household'],
                'household': ['labour', 'health', 'agriculture', 'education']
            }
            
            if question_domain in related_domains.get(intent.domain, []):
                return True
        
        # If no specific domain, include more questions
        if not intent.domain:
            return True
        
        # Keyword match in tags
        question_tags = [tag.lower() for tag in question.get('tags', [])]
        intent_keywords = [kw.lower() for kw in intent.keywords]
        
        if any(keyword in question_tags for keyword in intent_keywords):
            return True
        
        return False
    
    def _rank_questions(self, questions: List[Dict], intent: PromptIntent) -> List[Dict]:
        """Rank questions by relevance to intent."""
        for question in questions:
            score = question.get('relevance_score', 0)
            
            # Boost score for exact domain match
            if intent.domain and question.get('domain') == intent.domain:
                score += 0.5
            
            # Boost score for demographic questions (always needed)
            if question.get('category') == 'demographic':
                score += 0.3
            
            # Boost core questions
            if question.get('category') == 'core':
                score += 0.4
            
            # Boost economic questions for income-related prompts
            if question.get('category') == 'economic':
                economic_keywords = ['income', 'salary', 'earnings', 'revenue', 'turnover', 'expense']
                if any(kw in intent.keywords for kw in economic_keywords):
                    score += 0.3
                else:
                    score += 0.2
            
            # Boost score for keyword matches
            question_tags = [tag.lower() for tag in question.get('tags', [])]
            intent_keywords = [kw.lower() for kw in intent.keywords]
            matching_keywords = set(intent_keywords) & set(question_tags)
            score += len(matching_keywords) * 0.2
            
            # Boost score for official sources
            if question.get('source') in ['NSS', 'NFHS', 'PLFS', 'ASI']:
                score += 0.1
            
            # Boost questions with routing (more sophisticated)
            if question.get('routing'):
                score += 0.1
            
            question['final_score'] = score
        
        return sorted(questions, key=lambda x: x.get('final_score', 0), reverse=True)
    
    def _fallback_retrieval(self, intent: PromptIntent, max_questions: int) -> List[Dict]:
        """Fallback retrieval using simple keyword matching."""
        logger.info("Using fallback retrieval method")
        
        questions = self._load_questions()
        
        # Filter by domain
        if intent.domain:
            domain_questions = [q for q in questions if q.get('domain') in [intent.domain, 'demographic']]
            if domain_questions:
                questions = domain_questions
        
        # Simple keyword scoring
        for question in questions:
            score = 0
            question_text = str(question.get('text', '')).lower()
            question_tags = [tag.lower() for tag in question.get('tags', [])]
            
            # Score based on keyword matches
            for keyword in intent.keywords:
                if keyword.lower() in question_text:
                    score += 2
                if keyword.lower() in question_tags:
                    score += 1
            
            # Boost demographic questions
            if question.get('category') == 'demographic':
                score += 1
            
            question['relevance_score'] = score
        
        # Sort by score and return top results
        questions.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
        return questions[:max_questions]