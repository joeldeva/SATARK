"""RAG (Retrieval Augmented Generation) engine for question retrieval."""

import json
import numpy as np
from typing import List, Dict, Optional, Any
from pathlib import Path
import logging
from sentence_transformers import SentenceTransformer
import faiss

from ..models.prompt import PromptIntent

# Import config with proper path handling
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))
from config import KNOWLEDGE_BASE_DIR, EMBEDDING_MODEL, TOP_K_QUESTIONS

logger = logging.getLogger(__name__)


class RAGEngine:
    """RAG engine for retrieving relevant questions from knowledge base."""
    
    def __init__(self):
        """Initialize the RAG engine."""
        self.model = None
        self.index = None
        self.questions_db = []
        self.embeddings_path = KNOWLEDGE_BASE_DIR / "embeddings" / "question_vectors.faiss"
        self.questions_path = KNOWLEDGE_BASE_DIR / "embeddings" / "questions_metadata.json"
        
        self._load_or_create_embeddings()
    
    def retrieve_questions(self, intent: PromptIntent, max_questions: int = TOP_K_QUESTIONS) -> List[Dict]:
        """Retrieve relevant questions based on intent."""
        if not self.model or not self.index:
            logger.warning("RAG engine not properly initialized, using fallback")
            return self._fallback_retrieval(intent, max_questions)
        
        # Create query from intent
        query = self._create_query_from_intent(intent)
        
        # Get embeddings for query
        query_embedding = self.model.encode([query])
        
        # Search in FAISS index
        scores, indices = self.index.search(query_embedding.astype('float32'), max_questions * 2)
        
        # Filter and rank results
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < len(self.questions_db):
                question = self.questions_db[idx].copy()
                question['relevance_score'] = float(score)
                
                # Apply filters
                if self._matches_intent(question, intent):
                    results.append(question)
        
        # Sort by relevance and domain match
        results = self._rank_questions(results, intent)
        
        return results[:max_questions]
    
    def _load_or_create_embeddings(self):
        """Load existing embeddings or create new ones."""
        try:
            # Try to load existing embeddings
            if self.embeddings_path.exists() and self.questions_path.exists():
                self._load_embeddings()
            else:
                self._create_embeddings()
        except Exception as e:
            logger.error(f"Error with embeddings: {e}")
            logger.info("Falling back to rule-based retrieval")
    
    def _load_embeddings(self):
        """Load pre-computed embeddings."""
        try:
            # Load FAISS index
            self.index = faiss.read_index(str(self.embeddings_path))
            
            # Load questions metadata
            with open(self.questions_path, 'r', encoding='utf-8') as f:
                self.questions_db = json.load(f)
            
            # Load sentence transformer model
            self.model = SentenceTransformer(EMBEDDING_MODEL)
            
            logger.info(f"Loaded {len(self.questions_db)} questions with embeddings")
            
        except Exception as e:
            logger.error(f"Error loading embeddings: {e}")
            self._create_embeddings()
    
    def _create_embeddings(self):
        """Create embeddings from question files."""
        try:
            # Load sentence transformer model
            self.model = SentenceTransformer(EMBEDDING_MODEL)
            
            # Load all question files
            questions = []
            question_files = [
                "labour_questions.json",
                "health_questions.json", 
                "demographic_questions.json"
            ]
            
            for file_name in question_files:
                file_path = KNOWLEDGE_BASE_DIR / "questions" / file_name
                if file_path.exists():
                    with open(file_path, 'r', encoding='utf-8') as f:
                        file_questions = json.load(f)
                        questions.extend(file_questions)
            
            if not questions:
                logger.warning("No questions found to create embeddings")
                return
            
            # Create text representations for embedding
            question_texts = []
            for q in questions:
                text = self._create_question_text(q)
                question_texts.append(text)
            
            # Generate embeddings
            embeddings = self.model.encode(question_texts)
            
            # Create FAISS index
            dimension = embeddings.shape[1]
            self.index = faiss.IndexFlatIP(dimension)  # Inner product for similarity
            
            # Normalize embeddings for cosine similarity
            faiss.normalize_L2(embeddings.astype('float32'))
            self.index.add(embeddings.astype('float32'))
            
            # Save embeddings and metadata
            self.embeddings_path.parent.mkdir(parents=True, exist_ok=True)
            faiss.write_index(self.index, str(self.embeddings_path))
            
            with open(self.questions_path, 'w', encoding='utf-8') as f:
                json.dump(questions, f, ensure_ascii=False, indent=2)
            
            self.questions_db = questions
            
            logger.info(f"Created embeddings for {len(questions)} questions")
            
        except Exception as e:
            logger.error(f"Error creating embeddings: {e}")
            # Set to None to trigger fallback
            self.model = None
            self.index = None
    
    def _create_question_text(self, question: Dict) -> str:
        """Create text representation of question for embedding."""
        parts = []
        
        # Add question text
        if isinstance(question.get('question'), dict):
            parts.append(question['question'].get('en', ''))
        else:
            parts.append(str(question.get('question', '')))
        
        # Add keywords
        if question.get('keywords'):
            parts.extend(question['keywords'])
        
        # Add domain and category
        parts.append(question.get('domain', ''))
        parts.append(question.get('category', ''))
        
        # Add audience
        if question.get('audience'):
            parts.extend(question['audience'])
        
        return ' '.join(filter(None, parts))
    
    def _create_query_from_intent(self, intent: PromptIntent) -> str:
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
        # Domain match
        if intent.domain and question.get('domain') != intent.domain:
            # Allow 'all' domain questions
            if question.get('domain') != 'all':
                return False
        
        # Audience match
        if intent.audience:
            question_audience = question.get('audience', [])
            if 'all' not in question_audience:
                # Check if any audience keyword matches
                audience_words = intent.audience.lower().split()
                if not any(word in ' '.join(question_audience).lower() for word in audience_words):
                    return False
        
        return True
    
    def _rank_questions(self, questions: List[Dict], intent: PromptIntent) -> List[Dict]:
        """Rank questions by relevance to intent."""
        for question in questions:
            score = question.get('relevance_score', 0)
            
            # Boost score for exact domain match
            if intent.domain and question.get('domain') == intent.domain:
                score += 0.2
            
            # Boost score for keyword matches
            question_keywords = question.get('keywords', [])
            matching_keywords = set(intent.keywords) & set(question_keywords)
            score += len(matching_keywords) * 0.1
            
            # Boost score for required questions
            if question.get('required', False):
                score += 0.1
            
            question['final_score'] = score
        
        return sorted(questions, key=lambda x: x.get('final_score', 0), reverse=True)
    
    def _fallback_retrieval(self, intent: PromptIntent, max_questions: int) -> List[Dict]:
        """Fallback retrieval using simple keyword matching."""
        logger.info("Using fallback retrieval method")
        
        # Load questions directly from files
        questions = []
        question_files = [
            "labour_questions.json",
            "health_questions.json",
            "demographic_questions.json"
        ]
        
        for file_name in question_files:
            file_path = KNOWLEDGE_BASE_DIR / "questions" / file_name
            if file_path.exists():
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        file_questions = json.load(f)
                        questions.extend(file_questions)
                except Exception as e:
                    logger.error(f"Error loading {file_name}: {e}")
        
        # Filter by domain
        if intent.domain:
            questions = [q for q in questions if q.get('domain') in [intent.domain, 'all']]
        
        # Simple keyword scoring
        for question in questions:
            score = 0
            question_text = str(question.get('question', '')).lower()
            question_keywords = [k.lower() for k in question.get('keywords', [])]
            
            # Score based on keyword matches
            for keyword in intent.keywords:
                if keyword.lower() in question_text:
                    score += 2
                if keyword.lower() in question_keywords:
                    score += 1
            
            # Boost required questions
            if question.get('required', False):
                score += 1
            
            question['relevance_score'] = score
        
        # Sort by score and return top results
        questions.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
        return questions[:max_questions]