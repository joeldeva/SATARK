"""
SATARK - Survey Analysis, Tracking And Response Knowledge
"Vigilant Data Collection for Vigilant India"
"""

import logging
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Ensure backend root is on path
sys.path.insert(0, str(Path(__file__).parent))

from app.config import settings
from app.database import init_db, get_db
from utils.knowledge_loader import KnowledgeBaseLoader
from services.prompt_parser import PromptParser
from services.rag_engine import RAGEngine
from services.rule_engine import RuleEngine
from services.survey_generator import SurveyGenerator
from api.routes import router, set_generator, set_db_dependency

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="Deterministic Survey Intelligence Platform for Government of India",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/v1")


@app.on_event("startup")
async def startup():
    logger.info("🚀 Starting SATARK...")

    # Init DB (skip if no DB configured)
    try:
        init_db()
    except Exception as e:
        logger.warning(f"⚠️  DB init skipped: {e}")

    # Load knowledge base
    kb_path = settings.KNOWLEDGE_BASE_PATH
    kb = KnowledgeBaseLoader(base_path=kb_path).load_all()

    # Init engines
    prompt_parser = PromptParser()
    rag_engine = RAGEngine(kb)
    rag_engine.build_index()
    rule_engine = RuleEngine(kb)

    generator = SurveyGenerator(prompt_parser, rag_engine, rule_engine)
    set_generator(generator)
    set_db_dependency(get_db)

    logger.info("✅ SATARK ready")


@app.get("/")
async def root():
    return {
        "system": "SATARK",
        "full_name": "Survey Analysis, Tracking And Response Knowledge",
        "tagline": "Vigilant Data Collection for Vigilant India",
        "version": settings.VERSION,
        "status": "operational",
        "docs": "/docs"
    }


@app.get("/health")
async def health():
    return {"status": "healthy", "system": "SATARK"}


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"error": str(exc), "system": "SATARK"})


if __name__ == "__main__":
    import uvicorn
    print("=" * 60)
    print("🇮🇳  SATARK - Survey Intelligence Platform")
    print("   सतर्क - Vigilant Data Collection for Vigilant India")
    print(f"📍  http://localhost:8001")
    print(f"📚  Docs: http://localhost:8001/docs")
    print("=" * 60)
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True, log_level="info")
