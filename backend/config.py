"""Configuration settings for the AI Survey Generator."""

import os
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).parent.parent
KNOWLEDGE_BASE_DIR = BASE_DIR / "knowledge_base"
SCHEMAS_DIR = BASE_DIR / "schemas"

# API Configuration
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", 8000))
DEBUG = os.getenv("DEBUG", "true").lower() == "true"

# Knowledge Base Paths
QUESTIONS_DIR = KNOWLEDGE_BASE_DIR / "questions"
STANDARDS_DIR = KNOWLEDGE_BASE_DIR / "standards"
EMBEDDINGS_DIR = KNOWLEDGE_BASE_DIR / "embeddings"

# Survey Generation Settings
MAX_QUESTIONS = 50
MIN_QUESTIONS = 3
DEFAULT_LANGUAGE = "en"
SUPPORTED_LANGUAGES = ["en", "hi", "bn", "te", "ta", "mr", "gu", "kn", "ml", "or"]

# MoSPI Standards
MOSPI_DOMAINS = [
    "labour",
    "health", 
    "education",
    "agriculture",
    "household",
    "enterprise"
]

SURVEY_STANDARDS = [
    "NSS",      # National Sample Survey
    "NFHS",     # National Family Health Survey
    "PLFS",     # Periodic Labour Force Survey
    "ASI",      # Annual Survey of Industries
    "Custom"
]

# GSBPM Phases
GSBPM_PHASES = [
    "design",
    "build", 
    "collect",
    "process",
    "analyse",
    "disseminate"
]

# Question Categories (for ordering)
QUESTION_CATEGORIES = {
    "demographic": 1,    # Age, gender, location first
    "core": 2,          # Main survey questions
    "sensitive": 3,     # Income, personal topics
    "follow_up": 4      # Additional details
}

# Validation Rules
VALIDATION_RULES = {
    "age": {"min": 0, "max": 120},
    "income": {"min": 0, "max": 10000000},
    "household_size": {"min": 1, "max": 50},
    "years_experience": {"min": 0, "max": 60}
}

# RAG Configuration
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
VECTOR_STORE_PATH = EMBEDDINGS_DIR / "question_vectors.faiss"
TOP_K_QUESTIONS = 20

# Rule Engine Settings
MANDATORY_DEMOGRAPHICS = ["age", "gender", "location"]
AUTO_CODING_ENABLED = True

# Deployment Channels
DEPLOYMENT_CHANNELS = [
    "web",
    "whatsapp", 
    "ivr",
    "mobile_app",
    "paper"
]