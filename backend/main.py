"""Main entry point for the AI Survey Generator backend."""

import sys
import os
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

# Add the parent directory to access config
parent_dir = backend_dir.parent
sys.path.insert(0, str(parent_dir))

import time
import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Import our models and engines
from app.models.prompt import GenerationRequest, GenerationResponse
from app.engines.prompt_parser import PromptParser
from app.engines.survey_builder import SurveyBuilder

# Import config
try:
    from config import DEBUG, MOSPI_DOMAINS, SUPPORTED_LANGUAGES, SURVEY_STANDARDS
except ImportError:
    # Fallback values if config import fails
    DEBUG = True
    MOSPI_DOMAINS = ["labour", "health", "education", "agriculture", "household", "enterprise"]
    SUPPORTED_LANGUAGES = ["en", "hi", "bn", "te", "ta", "mr", "gu", "kn", "ml", "or"]
    SURVEY_STANDARDS = ["NSS", "NFHS", "PLFS", "ASI", "Custom"]

# Configure logging
logging.basicConfig(
    level=logging.INFO if not DEBUG else logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="AI Survey Generator",
    description="GSBPM-compliant, MoSPI-standard survey generation system",
    version="1.0.0",
    docs_url="/docs" if DEBUG else None,
    redoc_url="/redoc" if DEBUG else None
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize engines
try:
    prompt_parser = PromptParser()
    survey_builder = SurveyBuilder()
    logger.info("Engines initialized successfully")
except Exception as e:
    logger.error(f"Error initializing engines: {e}")
    prompt_parser = None
    survey_builder = None


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "AI Survey Generator API",
        "version": "1.0.0",
        "status": "running",
        "engines_loaded": prompt_parser is not None and survey_builder is not None
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "engines_status": {
            "prompt_parser": prompt_parser is not None,
            "survey_builder": survey_builder is not None
        }
    }


@app.post("/generate-survey", response_model=GenerationResponse)
async def generate_survey(request: GenerationRequest):
    """Generate a survey from a text prompt."""
    start_time = time.time()
    
    if not prompt_parser or not survey_builder:
        return GenerationResponse(
            success=False,
            survey=None,
            intent=None,
            errors=["Survey engines not properly initialized"],
            warnings=[],
            processing_time=time.time() - start_time
        )
    
    try:
        logger.info(f"Generating survey from prompt: {request.prompt[:100]}...")
        
        # Step 1: Parse the prompt to extract intent
        intent = prompt_parser.parse(request.prompt)
        logger.info(f"Extracted intent: {intent.dict()}")
        
        # Override intent with request parameters if provided
        if request.domain:
            intent.domain = request.domain
        if request.language:
            intent.language = request.language
        
        # Step 2: Build the survey
        survey = survey_builder.build_survey(intent, request.max_questions)
        
        # Step 3: Convert to dict for response
        survey_dict = survey.dict()
        
        processing_time = time.time() - start_time
        
        # Generate warnings if needed
        warnings = []
        if len(survey.questions) < 3:
            warnings.append("Survey has very few questions. Consider adding more details to your prompt.")
        if not intent.domain:
            warnings.append("Could not determine survey domain. Using default classification.")
        
        return GenerationResponse(
            success=True,
            survey=survey_dict,
            intent=intent,
            errors=[],
            warnings=warnings,
            processing_time=processing_time
        )
        
    except Exception as e:
        logger.error(f"Error generating survey: {str(e)}", exc_info=True)
        
        processing_time = time.time() - start_time
        
        return GenerationResponse(
            success=False,
            survey=None,
            intent=None,
            errors=[f"Survey generation failed: {str(e)}"],
            warnings=[],
            processing_time=processing_time
        )


@app.post("/parse-prompt")
async def parse_prompt(request: dict):
    """Parse a prompt and return extracted intent (for debugging)."""
    try:
        if not prompt_parser:
            raise HTTPException(status_code=500, detail="Prompt parser not initialized")
        
        prompt = request.get("prompt", "")
        intent = prompt_parser.parse(prompt)
        return {
            "success": True,
            "intent": intent.dict()
        }
    except Exception as e:
        logger.error(f"Error parsing prompt: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/domains")
async def get_domains():
    """Get available survey domains."""
    return {
        "domains": MOSPI_DOMAINS,
        "description": "Available MoSPI survey domains"
    }


@app.get("/languages")
async def get_languages():
    """Get supported languages."""
    return {
        "languages": SUPPORTED_LANGUAGES,
        "description": "Supported survey languages"
    }


@app.get("/standards")
async def get_standards():
    """Get available survey standards."""
    return {
        "standards": SURVEY_STANDARDS,
        "description": "Available survey standards"
    }


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": str(exc) if DEBUG else "An error occurred"
        }
    )


if __name__ == "__main__":
    import uvicorn
    
    # Default configuration
    API_HOST = "0.0.0.0"
    API_PORT = 8000
    
    print("🚀 Starting AI Survey Generator Backend")
    print(f"📍 Server: http://{API_HOST}:{API_PORT}")
    print(f"📚 API Docs: http://{API_HOST}:{API_PORT}/docs")
    print("=" * 50)
    
    uvicorn.run(
        "main:app",
        host=API_HOST,
        port=API_PORT,
        reload=DEBUG,
        log_level="info"
    )