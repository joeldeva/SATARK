import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

sys.path.insert(0, str(Path(__file__).parent))

from api.routes import router, set_db_dependency, set_generator
from api.rag_routes import router as rag_router, set_db_dependency as set_rag_db_dependency
from api.event_routes import router as event_router
from api.channel_routes import router as channel_router, set_db_dependency as set_channel_db_dependency
from api.whatsapp import router as whatsapp_router, set_db_dependency as set_whatsapp_db_dependency
from app.config import settings
from app.database import SessionLocal, get_db, init_db
from app.runtime_checks import assert_required_runtime, readiness
from app.seed import seed_core_data
from services.prompt_parser import PromptParser
from services.rag_engine import RAGEngine
from services.rule_engine import RuleEngine
from services.survey_generator import SurveyGenerator
from services.llm_planner import LocalLLMPlanner, OpenRouterPlanner
from utils.knowledge_loader import KnowledgeBaseLoader

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting SATARK")
    if settings.DATABASE_URL.startswith("sqlite"):
        init_db()
    else:
        assert_required_runtime()
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
    provider = settings.LLM_PROVIDER.lower()
    if provider == "ollama":
        llm_planner = LocalLLMPlanner(
            model=settings.LLM_MODEL,
            base_url=settings.OLLAMA_BASE_URL,
            timeout_seconds=settings.LLM_TIMEOUT_SECONDS,
            required=settings.LLM_REQUIRED,
        )
        logger.info("Local LLM planner enabled: %s via %s", settings.LLM_MODEL, settings.OLLAMA_BASE_URL)
    elif provider == "openrouter":
        if not settings.OPENROUTER_API_KEY:
            raise RuntimeError("LLM_PROVIDER=openrouter requires OPENROUTER_API_KEY")
        else:
            openrouter_timeout = min(settings.LLM_TIMEOUT_SECONDS, 45)
            openrouter_model = settings.OPENROUTER_MODEL
            if openrouter_model in {"nex-agi/nex-n2-pro:free", "google/gemma-4-26b-a4b-it:free"}:
                openrouter_model = "google/gemma-4-31b-it:free"
            llm_planner = OpenRouterPlanner(
                model=openrouter_model,
                api_key=settings.OPENROUTER_API_KEY,
                base_url=settings.OPENROUTER_BASE_URL,
                timeout_seconds=openrouter_timeout,
                required=settings.LLM_REQUIRED,
            )
            logger.info(
                "OpenRouter LLM planner enabled: %s via %s (timeout=%ss)",
                openrouter_model,
                settings.OPENROUTER_BASE_URL,
                openrouter_timeout,
            )
    elif provider != "none":
        if settings.LLM_REQUIRED:
            raise RuntimeError(f"Unsupported LLM_PROVIDER: {settings.LLM_PROVIDER}")
        logger.warning("Unsupported LLM_PROVIDER=%s; survey assist will use deterministic fallback", settings.LLM_PROVIDER)
    generator = SurveyGenerator(prompt_parser, rag_engine, rule_engine, llm_planner=llm_planner)

    set_generator(generator)
    set_db_dependency(get_db)
    set_rag_db_dependency(get_db)
    set_whatsapp_db_dependency(get_db)
    set_channel_db_dependency(get_db)
    logger.info("SATARK ready")
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="Deterministic survey intelligence platform",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
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
app.include_router(rag_router, prefix="/api")
app.include_router(event_router, prefix="/api")
app.include_router(channel_router, prefix="/api/v1")
app.include_router(whatsapp_router, prefix="/api")


@app.options("/{full_path:path}")
async def options_preflight(full_path: str, request: Request):
    origin = request.headers.get("origin")
    allowed_origins = settings.cors_origins
    allow_origin = origin if origin in allowed_origins else (allowed_origins[0] if allowed_origins else "*")
    return Response(
        status_code=204,
        headers={
            "Access-Control-Allow-Origin": allow_origin,
            "Access-Control-Allow-Methods": "GET,POST,PUT,PATCH,DELETE,OPTIONS",
            "Access-Control-Allow-Headers": request.headers.get(
                "access-control-request-headers",
                "authorization,content-type",
            ),
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Max-Age": "86400",
            "Vary": "Origin",
        },
    )


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


@app.get("/health/ready")
async def health_ready():
    result = readiness()
    return JSONResponse(
        status_code=status.HTTP_200_OK if result["ready"] else status.HTTP_503_SERVICE_UNAVAILABLE,
        content=result,
    )


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error("Unhandled exception: %s", exc, exc_info=True)
    return JSONResponse(status_code=500, content={"error": str(exc), "system": "SATARK"})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8001, reload=settings.DEBUG, log_level="info")
