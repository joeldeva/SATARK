"""
SATARK.AI Configuration
Deterministic Survey Intelligence Engine Settings
"""

import os
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).parent
DATABASE_DIR = BASE_DIR / "database"
ML_MODELS_DIR = BASE_DIR / "ml" / "models"

# API Configuration
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", 8000))
DEBUG = os.getenv("DEBUG", "true").lower() == "true"

# SATARK.AI System Configuration
SYSTEM_NAME = "SATARK.AI"
SYSTEM_VERSION = "1.0.0"
ARCHITECTURE = "Hybrid Statistical Intelligence"

# Survey Generation Limits
MAX_QUESTIONS = 50
MIN_QUESTIONS = 3
DEFAULT_QUESTIONS = 15

# Supported Languages (Government of India Official)
SUPPORTED_LANGUAGES = [
    "en",  # English
    "hi",  # Hindi
    "bn",  # Bengali
    "te",  # Telugu
    "ta",  # Tamil
    "mr",  # Marathi
    "gu",  # Gujarati
    "kn",  # Kannada
    "ml",  # Malayalam
    "or",  # Odia
    "pa",  # Punjabi
    "as",  # Assamese
    "ur"   # Urdu
]

# MoSPI Survey Domains
MOSPI_DOMAINS = [
    "labour",        # Employment, unemployment, wages
    "health",        # Healthcare access, outcomes
    "education",     # Literacy, enrollment, outcomes
    "agriculture",   # Farming, rural livelihoods
    "household",     # Living standards, consumption
    "enterprise",    # Business establishments
    "social",        # Social indicators
    "economic",      # Economic indicators
    "demographic"    # Population characteristics
]

# Official Survey Standards
SURVEY_STANDARDS = [
    "NSS",          # National Sample Survey
    "NFHS",         # National Family Health Survey
    "PLFS",         # Periodic Labour Force Survey
    "ASI",          # Annual Survey of Industries
    "AHS",          # Annual Health Survey
    "DLHS",         # District Level Health Survey
    "Custom"        # Custom surveys
]

# Question Categories (for ordering and validation)
QUESTION_CATEGORIES = {
    "demographic": 1,    # Age, gender, location (mandatory first)
    "core": 2,          # Main survey questions
    "economic": 3,      # Income, expenditure (sensitive)
    "social": 4,        # Social indicators
    "follow_up": 5      # Additional details
}

# Mandatory Demographic Questions
MANDATORY_DEMOGRAPHICS = [
    "age",
    "gender", 
    "location",
    "education"
]

# Validation Rules for Common Fields
VALIDATION_RULES = {
    "age": {"min": 0, "max": 120, "type": "integer"},
    "income": {"min": 0, "max": 10000000, "type": "integer", "sensitive": True},
    "household_size": {"min": 1, "max": 50, "type": "integer"},
    "working_hours": {"min": 0, "max": 168, "type": "integer"},
    "years_experience": {"min": 0, "max": 60, "type": "integer"},
    "education_years": {"min": 0, "max": 25, "type": "integer"}
}

# Machine Learning Configuration
ML_CONFIG = {
    # Embedding Model for Semantic Retrieval
    "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
    "embedding_dimension": 384,
    
    # Domain Classification
    "domain_classifier": {
        "model": "logistic_regression",
        "vectorizer": "tfidf",
        "max_features": 5000,
        "ngram_range": (1, 2)
    },
    
    # Anomaly Detection
    "anomaly_detector": {
        "model": "isolation_forest",
        "contamination": 0.1,
        "random_state": 42
    },
    
    # Vector Search
    "faiss_index_type": "IndexFlatIP",  # Inner Product for cosine similarity
    "top_k_questions": 20
}

# Database Paths
DATABASE_PATHS = {
    "question_bank": DATABASE_DIR / "question_bank.json",
    "routing_rules": DATABASE_DIR / "routing_rules.json", 
    "coding_standards": DATABASE_DIR / "coding_standards.json",
    "validation_rules": DATABASE_DIR / "validation_rules.json",
    "domain_samples": DATABASE_DIR / "domain_samples.json"
}

# Coding Standards (NCO/NIC/ISIC)
CODING_STANDARDS = {
    "occupation": "NCO-2015",      # National Classification of Occupations
    "industry": "NIC-2008",        # National Industrial Classification
    "economic_activity": "ISIC-4", # International Standard Industrial Classification
    "education": "ISCED-2011",     # International Standard Classification of Education
    "consumption": "COICOP-2018"   # Classification of Individual Consumption
}

# GSBPM Phases (Generic Statistical Business Process Model)
GSBPM_PHASES = [
    "specify_needs",    # Phase 1: Specify Needs
    "design",          # Phase 2: Design
    "build",           # Phase 3: Build
    "collect",         # Phase 4: Collect
    "process",         # Phase 5: Process
    "analyse",         # Phase 6: Analyse
    "disseminate",     # Phase 7: Disseminate
    "evaluate"         # Phase 8: Evaluate
]

# Deployment Channels
DEPLOYMENT_CHANNELS = [
    "web",             # Web application
    "mobile_app",      # Mobile application
    "whatsapp",        # WhatsApp bot
    "ivr",             # Interactive Voice Response
    "paper",           # Paper forms
    "tablet",          # Tablet-based surveys
    "capi",            # Computer Assisted Personal Interview
    "cati"             # Computer Assisted Telephone Interview
]

# Quality Assurance Thresholds
QUALITY_THRESHOLDS = {
    "validation_score_min": 80,     # Minimum validation score
    "question_relevance_min": 0.7,  # Minimum question relevance
    "response_time_max": 5.0,       # Maximum response time (seconds)
    "anomaly_threshold": 0.1        # Anomaly detection threshold
}

# Logging Configuration
LOGGING_CONFIG = {
    "level": "INFO",
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "file": "satark.log",
    "max_bytes": 10485760,  # 10MB
    "backup_count": 5
}

# Security Configuration
SECURITY_CONFIG = {
    "cors_origins": [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://satark.gov.in"
    ],
    "rate_limit": "100/minute",
    "max_request_size": "10MB"
}

# System Capabilities
SYSTEM_CAPABILITIES = {
    "deterministic": True,
    "hallucination_free": True,
    "offline_capable": True,
    "government_compliant": True,
    "auditable": True,
    "multilingual": True,
    "real_time": True,
    "scalable": True
}