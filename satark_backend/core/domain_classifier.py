"""
SATARK.AI Domain Classifier
ML-based domain classification using TF-IDF + Logistic Regression
"""

import pickle
import logging
from pathlib import Path
from typing import Optional, Dict, List
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
import numpy as np

from config import MOSPI_DOMAINS, ML_CONFIG, DATABASE_PATHS

logger = logging.getLogger(__name__)


class DomainClassifier:
    """
    ML-based domain classifier using explainable methods.
    Uses TF-IDF + Logistic Regression for transparency.
    """
    
    def __init__(self):
        """Initialize the domain classifier."""
        self.pipeline = None
        self.confidence_threshold = 0.6
        
        # Try to load pre-trained model
        model_path = Path(__file__).parent.parent / "ml" / "models" / "domain_classifier.pkl"
        
        if model_path.exists():
            self._load_model(model_path)
        else:
            logger.info("🔧 Training new domain classifier...")
            self._train_model()
    
    def classify(self, prompt: str) -> Optional[str]:
        """Classify prompt into MoSPI domain."""
        if not self.pipeline:
            logger.warning("⚠️ Domain classifier not available, using fallback")
            return self._fallback_classification(prompt)
        
        try:
            # Get prediction probabilities
            probabilities = self.pipeline.predict_proba([prompt])[0]
            classes = self.pipeline.classes_
            
            # Find best prediction
            best_idx = np.argmax(probabilities)
            best_prob = probabilities[best_idx]
            best_domain = classes[best_idx]
            
            logger.debug(f"Domain classification: {best_domain} (confidence: {best_prob:.2f})")
            
            # Return only if confidence is above threshold
            if best_prob >= self.confidence_threshold:
                return best_domain
            else:
                logger.debug(f"Low confidence ({best_prob:.2f}), using fallback")
                return self._fallback_classification(prompt)
                
        except Exception as e:
            logger.error(f"Error in domain classification: {e}")
            return self._fallback_classification(prompt)
    
    def get_confidence(self, prompt: str) -> float:
        """Get classification confidence."""
        if not self.pipeline:
            return 0.0
        
        try:
            probabilities = self.pipeline.predict_proba([prompt])[0]
            return float(np.max(probabilities))
        except Exception as e:
            logger.error(f"Error getting confidence: {e}")
            return 0.0
    
    def get_all_probabilities(self, prompt: str) -> Dict[str, float]:
        """Get probabilities for all domains."""
        if not self.pipeline:
            return {}
        
        try:
            probabilities = self.pipeline.predict_proba([prompt])[0]
            classes = self.pipeline.classes_
            return dict(zip(classes, probabilities))
        except Exception as e:
            logger.error(f"Error getting probabilities: {e}")
            return {}
    
    def _load_model(self, model_path: Path):
        """Load pre-trained model."""
        try:
            with open(model_path, 'rb') as f:
                self.pipeline = pickle.load(f)
            logger.info("✅ Domain classifier model loaded")
        except Exception as e:
            logger.error(f"❌ Error loading model: {e}")
            self._train_model()
    
    def _train_model(self):
        """Train domain classifier with sample data."""
        try:
            # Load training data
            training_data = self._get_training_data()
            
            if not training_data:
                logger.warning("⚠️ No training data available")
                return
            
            texts, labels = zip(*training_data)
            
            # Create pipeline
            self.pipeline = Pipeline([
                ('tfidf', TfidfVectorizer(
                    max_features=ML_CONFIG['domain_classifier']['max_features'],
                    ngram_range=ML_CONFIG['domain_classifier']['ngram_range'],
                    stop_words='english',
                    lowercase=True
                )),
                ('classifier', LogisticRegression(
                    random_state=42,
                    max_iter=1000
                ))
            ])
            
            # Train model
            self.pipeline.fit(texts, labels)
            
            # Save model
            model_dir = Path(__file__).parent.parent / "ml" / "models"
            model_dir.mkdir(parents=True, exist_ok=True)
            
            model_path = model_dir / "domain_classifier.pkl"
            with open(model_path, 'wb') as f:
                pickle.dump(self.pipeline, f)
            
            logger.info("✅ Domain classifier trained and saved")
            
        except Exception as e:
            logger.error(f"❌ Error training model: {e}")
            self.pipeline = None
    
    def _get_training_data(self) -> List[tuple]:
        """Get training data for domain classification."""
        # Sample training data for each domain
        training_samples = [
            # Labour domain
            ("survey about employment status and job satisfaction", "labour"),
            ("unemployment survey for youth", "labour"),
            ("worker salary and wage survey", "labour"),
            ("employment opportunities in rural areas", "labour"),
            ("job market analysis survey", "labour"),
            ("workforce participation survey", "labour"),
            
            # Health domain
            ("healthcare access survey for women", "health"),
            ("maternal health survey", "health"),
            ("hospital visit and treatment survey", "health"),
            ("health insurance coverage survey", "health"),
            ("disease prevalence survey", "health"),
            ("nutrition and health survey", "health"),
            
            # Education domain
            ("literacy survey for adults", "education"),
            ("school enrollment survey", "education"),
            ("education quality survey", "education"),
            ("student performance survey", "education"),
            ("teacher training survey", "education"),
            ("educational attainment survey", "education"),
            
            # Agriculture domain
            ("farming practices survey", "agriculture"),
            ("crop yield survey", "agriculture"),
            ("agricultural income survey", "agriculture"),
            ("livestock survey", "agriculture"),
            ("irrigation survey", "agriculture"),
            ("rural livelihood survey", "agriculture"),
            
            # Household domain
            ("household consumption survey", "household"),
            ("family living standards survey", "household"),
            ("housing conditions survey", "household"),
            ("household assets survey", "household"),
            ("domestic expenditure survey", "household"),
            ("family welfare survey", "household"),
            
            # Enterprise domain
            ("business establishment survey", "enterprise"),
            ("industrial survey", "enterprise"),
            ("msme survey", "enterprise"),
            ("commercial activity survey", "enterprise"),
            ("enterprise performance survey", "enterprise"),
            ("business growth survey", "enterprise"),
            
            # Social domain
            ("social indicators survey", "social"),
            ("community welfare survey", "social"),
            ("social inclusion survey", "social"),
            ("caste and religion survey", "social"),
            ("social development survey", "social"),
            ("cultural practices survey", "social"),
            
            # Economic domain
            ("economic indicators survey", "economic"),
            ("poverty survey", "economic"),
            ("financial inclusion survey", "economic"),
            ("economic development survey", "economic"),
            ("income distribution survey", "economic"),
            ("economic welfare survey", "economic"),
            
            # Demographic domain
            ("population survey", "demographic"),
            ("demographic characteristics survey", "demographic"),
            ("migration survey", "demographic"),
            ("age and gender survey", "demographic"),
            ("population growth survey", "demographic"),
            ("census survey", "demographic")
        ]
        
        # Try to load additional samples from database
        try:
            if DATABASE_PATHS['domain_samples'].exists():
                import json
                with open(DATABASE_PATHS['domain_samples'], 'r') as f:
                    additional_samples = json.load(f)
                    for sample in additional_samples:
                        training_samples.append((sample['text'], sample['domain']))
        except Exception as e:
            logger.debug(f"Could not load additional samples: {e}")
        
        return training_samples
    
    def _fallback_classification(self, prompt: str) -> Optional[str]:
        """Fallback classification using keyword matching."""
        prompt_lower = prompt.lower()
        
        # Simple keyword-based classification
        domain_keywords = {
            "labour": ["employment", "job", "work", "salary", "wage", "unemployment"],
            "health": ["health", "medical", "hospital", "doctor", "disease", "healthcare"],
            "education": ["education", "school", "literacy", "student", "teacher"],
            "agriculture": ["agriculture", "farming", "crop", "farmer", "livestock"],
            "household": ["household", "family", "home", "housing", "consumption"],
            "enterprise": ["business", "enterprise", "industry", "commercial", "msme"],
            "social": ["social", "community", "caste", "religion", "cultural"],
            "economic": ["economic", "poverty", "financial", "income", "wealth"],
            "demographic": ["population", "demographic", "census", "migration", "age"]
        }
        
        domain_scores = {}
        for domain, keywords in domain_keywords.items():
            score = sum(1 for keyword in keywords if keyword in prompt_lower)
            if score > 0:
                domain_scores[domain] = score
        
        if domain_scores:
            return max(domain_scores, key=domain_scores.get)
        
        return None