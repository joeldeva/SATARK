import logging
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

sys.path.insert(0, str(Path(__file__).parent))

from api.routes import router, set_db_dependency, set_generator
from app.config import settings
from app.database import SessionLocal, get_db, init_db
from app.seed import seed_core_data
from services.prompt_parser import PromptParser
from services.rag_engine import RAGEngine
from services.rule_engine import RuleEngine
from services.survey_generator import SurveyGenerator
from services.llm_planner import LocalLLMPlanner
from utils.knowledge_loader import KnowledgeBaseLoader

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="Deterministic survey intelligence platform",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")
app.include_router(router, prefix="/api/v1")


@app.on_event("startup")
async def startup():
    logger.info("Starting SATARK")
    init_db()
    db = SessionLocal()
    try:
        seed_core_data(db, settings.PROJECT_ROOT)
    finally:
        db.close()

    kb = KnowledgeBaseLoader(base_path=settings.KNOWLEDGE_BASE_PATH).load_all()
    prompt_parser = PromptParser()
    rag_engine = RAGEngine(kb).build_index()
    rule_engine = RuleEngine(kb)
    llm_planner = None
    if settings.LLM_PROVIDER.lower() == "ollama":
        llm_planner = LocalLLMPlanner(
            model=settings.LLM_MODEL,
            base_url=settings.OLLAMA_BASE_URL,
            timeout_seconds=settings.LLM_TIMEOUT_SECONDS,
            required=settings.LLM_REQUIRED,
        )
        logger.info("Local LLM planner enabled: %s via %s", settings.LLM_MODEL, settings.OLLAMA_BASE_URL)
    elif settings.LLM_PROVIDER.lower() != "none":
        raise RuntimeError(f"Unsupported LLM_PROVIDER: {settings.LLM_PROVIDER}")
    generator = SurveyGenerator(prompt_parser, rag_engine, rule_engine, llm_planner=llm_planner)

    set_generator(generator)
    set_db_dependency(get_db)
    logger.info("SATARK ready")


@app.get("/")
async def root():
    return {
        "system": "SATARK",
        "full_name": "Survey Analysis, Tracking And Response Knowledge",
        "version": settings.VERSION,
        "status": "operational",
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    return {"status": "healthy", "system": "SATARK", "version": settings.VERSION}


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error("Unhandled exception: %s", exc, exc_info=True)
    return JSONResponse(status_code=500, content={"error": str(exc), "system": "SATARK"})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8001, reload=settings.DEBUG, log_level="info")
