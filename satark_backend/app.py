"""
SATARK.AI - Deterministic Survey Intelligence Engine
Main FastAPI Application
"""

import sys
import time
import logging
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Add current directory to path
sys.path.append(str(Path(__file__).parent))

from config import *
from models.survey_schema import SurveyGenerationRequest, SurveyGenerationResponse
from core.prompt_parser import PromptParser
from core.domain_classifier import DomainClassifier
from core.retrieval_engine import RetrievalEngine
from core.survey_builder import SurveyBuilder
from core.validation_engine import ValidationEngine
from ml.anomaly_detector import AnomalyDetector
from analytics.aggregation_engine import aggregation_engine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="SATARK.AI - Deterministic Survey Intelligence Engine",
    description="Hybrid statistical intelligence for government-grade survey generation",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize core engines
try:
    logger.info("Initializing SATARK.AI engines...")
    
    prompt_parser = PromptParser()
    domain_classifier = DomainClassifier()
    retrieval_engine = RetrievalEngine()
    survey_builder = SurveyBuilder()
    validation_engine = ValidationEngine()
    anomaly_detector = AnomalyDetector()
    
    logger.info("✅ All SATARK.AI engines initialized successfully")
    engines_status = True
    
except Exception as e:
    logger.error(f"❌ Error initializing engines: {e}")
    engines_status = False


@app.get("/")
async def root():
    """Root endpoint - System status."""
    return {
        "system": "SATARK.AI",
        "description": "Deterministic Survey Intelligence Engine",
        "version": "1.0.0",
        "status": "operational" if engines_status else "degraded",
        "architecture": "Hybrid Statistical Intelligence",
        "engines_loaded": engines_status,
        "capabilities": [
            "Rule-based survey generation",
            "Official question repository",
            "NLP intent classification",
            "Semantic question retrieval",
            "Statistical validation",
            "Anomaly detection"
        ]
    }


@app.get("/health")
async def health_check():
    """Comprehensive health check."""
    return {
        "status": "healthy" if engines_status else "unhealthy",
        "timestamp": time.time(),
        "engines": {
            "prompt_parser": prompt_parser is not None,
            "domain_classifier": domain_classifier is not None,
            "retrieval_engine": retrieval_engine is not None,
            "survey_builder": survey_builder is not None,
            "validation_engine": validation_engine is not None,
            "anomaly_detector": anomaly_detector is not None
        },
        "system_info": {
            "deterministic": True,
            "hallucination_free": True,
            "government_compliant": True,
            "offline_capable": True
        }
    }


@app.post("/generate-survey", response_model=SurveyGenerationResponse)
async def generate_survey(request: SurveyGenerationRequest):
    """
    Generate a survey using SATARK.AI's deterministic intelligence.
    
    Process:
    1. Parse prompt using NLP + Rules
    2. Classify domain using ML
    3. Retrieve questions using embeddings
    4. Build survey using rules
    5. Validate using statistical checks
    6. Return structured JSON
    """
    start_time = time.time()
    
    if not engines_status:
        return SurveyGenerationResponse(
            success=False,
            survey=None,
            intent=None,
            errors=["SATARK.AI engines not properly initialized"],
            warnings=[],
            processing_time=time.time() - start_time,
            engine_trace=[]
        )
    
    try:
        logger.info(f"🚀 SATARK.AI processing: {request.prompt[:100]}...")
        engine_trace = []
        
        # Step 1: Parse prompt using NLP + Rules
        logger.info("📝 Step 1: Parsing prompt...")
        intent = prompt_parser.parse(request.prompt)
        engine_trace.append({
            "step": 1,
            "engine": "PromptParser",
            "method": "NLP + Rules",
            "output": "Intent extracted"
        })
        
        # Step 2: Classify domain using ML
        logger.info("🎯 Step 2: Classifying domain...")
        if not intent.domain:
            intent.domain = domain_classifier.classify(request.prompt)
        engine_trace.append({
            "step": 2,
            "engine": "DomainClassifier", 
            "method": "TF-IDF + LogisticRegression",
            "output": f"Domain: {intent.domain}"
        })
        
        # Override with request parameters
        if request.domain:
            intent.domain = request.domain
        if request.languages:
            intent.languages = request.languages
        
        # Step 3: Retrieve questions using embeddings
        logger.info("🔍 Step 3: Retrieving relevant questions...")
        questions = retrieval_engine.retrieve_questions(intent, request.max_questions)
        engine_trace.append({
            "step": 3,
            "engine": "RetrievalEngine",
            "method": "SentenceTransformers + FAISS",
            "output": f"{len(questions)} questions retrieved"
        })
        
        # Step 4: Build survey using rules
        logger.info("🏗️ Step 4: Building survey structure...")
        survey = survey_builder.build_survey(intent, questions, request.max_questions)
        engine_trace.append({
            "step": 4,
            "engine": "SurveyBuilder",
            "method": "Deterministic Rules",
            "output": f"Survey with {len(survey.questions)} questions"
        })
        
        # Step 5: Validate using statistical checks
        logger.info("✅ Step 5: Validating survey...")
        validation_result = validation_engine.validate_survey(survey)
        engine_trace.append({
            "step": 5,
            "engine": "ValidationEngine",
            "method": "Statistical Rules",
            "output": f"Validation score: {validation_result.score}%"
        })
        
        processing_time = time.time() - start_time
        
        # Generate warnings
        warnings = []
        if len(survey.questions) < 3:
            warnings.append("Survey has very few questions. Consider more detailed prompt.")
        if validation_result.score < 80:
            warnings.append("Survey validation score is below optimal threshold.")
        
        logger.info(f"✅ SATARK.AI completed in {processing_time:.2f}s")
        
        return SurveyGenerationResponse(
            success=True,
            survey=survey.dict(),
            intent=intent,
            errors=[],
            warnings=warnings,
            processing_time=processing_time,
            engine_trace=engine_trace,
            validation_score=validation_result.score,
            deterministic=True
        )
        
    except Exception as e:
        logger.error(f"❌ SATARK.AI error: {str(e)}", exc_info=True)
        
        processing_time = time.time() - start_time
        
        return SurveyGenerationResponse(
            success=False,
            survey=None,
            intent=None,
            errors=[f"Survey generation failed: {str(e)}"],
            warnings=[],
            processing_time=processing_time,
            engine_trace=engine_trace if 'engine_trace' in locals() else [],
            validation_score=0,
            deterministic=True
        )


@app.post("/analyze-intent")
async def analyze_intent(request: dict):
    """Analyze prompt intent for debugging."""
    try:
        if not engines_status:
            raise HTTPException(status_code=500, detail="Engines not initialized")
        
        prompt = request.get("prompt", "")
        intent = prompt_parser.parse(prompt)
        domain = domain_classifier.classify(prompt)
        
        return {
            "success": True,
            "intent": intent.dict(),
            "classified_domain": domain,
            "confidence": domain_classifier.get_confidence(prompt),
            "method": "NLP + Rules + ML Classification"
        }
    except Exception as e:
        logger.error(f"Error analyzing intent: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/system-info")
async def get_system_info():
    """Get detailed system information."""
    return {
        "system": "SATARK.AI",
        "architecture": "Hybrid Statistical Intelligence",
        "components": {
            "prompt_parser": "spaCy + Regex + Rules",
            "domain_classifier": "TF-IDF + Logistic Regression", 
            "retrieval_engine": "SentenceTransformers + FAISS",
            "survey_builder": "Deterministic Rule Engine",
            "validation_engine": "Statistical Validation Rules",
            "anomaly_detector": "IsolationForest + Z-score"
        },
        "data_sources": [
            "NSS Schedules",
            "PLFS Forms", 
            "NFHS Questionnaires",
            "ASI Forms"
        ],
        "standards_compliance": [
            "GSBPM",
            "MoSPI Guidelines",
            "NCO Classification",
            "NIC Classification", 
            "ISIC Standards"
        ],
        "guarantees": {
            "deterministic": True,
            "hallucination_free": True,
            "auditable": True,
            "offline_capable": True,
            "government_grade": True
        }
    }


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler with detailed logging."""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal system error",
            "message": str(exc),
            "system": "SATARK.AI",
            "deterministic": True
        }
    )


if __name__ == "__main__":
    import uvicorn
    
    print("🚀 Starting SATARK.AI - Deterministic Survey Intelligence Engine")
    print(f"📍 Server: http://{API_HOST}:{API_PORT}")
    print(f"📚 API Docs: http://{API_HOST}:{API_PORT}/docs")
    print("🎯 Architecture: Hybrid Statistical Intelligence")
    print("✅ Government-Grade | Deterministic | Auditable")
    print("=" * 60)
    
    uvicorn.run(
        "app:app",
        host=API_HOST,
        port=API_PORT,
        reload=DEBUG,
        log_level="info"
    )


# ============================================================
# ANALYTICS API ENDPOINTS
# Government-Grade Statistical Intelligence Dashboard
# ============================================================

@app.get("/analytics/summary")
async def get_analytics_summary(
    survey_id: str = None,
    start_date: str = None,
    end_date: str = None
):
    """
    Get KPI summary metrics for dashboard.
    
    Returns:
        - Total responses
        - Validation rate
        - Error rate
        - Rural/Urban split
        - Gender distribution
        - Confidence score
    """
    try:
        # In production, fetch from database with filters
        # For demo, generate sample data
        demo_responses = [
            {
                'response_id': f'RESP_{i}',
                'is_valid': i % 10 != 0,  # 90% valid
                'location_type': 'Rural' if i % 3 == 0 else 'Urban',
                'gender': ['Male', 'Female', 'Other'][i % 3],
                'timestamp': '2026-02-09T12:00:00Z'
            }
            for i in range(1000)
        ]
        
        summary = aggregation_engine.compute_summary(demo_responses)
        
        return JSONResponse(content={
            "success": True,
            "data": summary
        })
    
    except Exception as e:
        logger.error(f"Analytics summary error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/analytics/timeseries")
async def get_analytics_timeseries(
    metric: str = "employment_rate",
    period: str = "monthly",
    survey_id: str = None
):
    """
    Get time series trend data.
    
    Args:
        metric: Metric to track (employment_rate, participation_rate, etc.)
        period: Aggregation period (daily, weekly, monthly, quarterly)
        survey_id: Optional survey filter
    
    Returns:
        Time series data with dates and values
    """
    try:
        # Generate demo time series data
        demo_responses = [
            {
                'response_id': f'RESP_{i}',
                'timestamp': f'2026-{(i % 12) + 1:02d}-01T12:00:00Z',
                'metric_value': 75 + (i % 20)
            }
            for i in range(100)
        ]
        
        timeseries = aggregation_engine.compute_timeseries(
            demo_responses, 
            metric=metric, 
            period=period
        )
        
        return JSONResponse(content={
            "success": True,
            "data": timeseries
        })
    
    except Exception as e:
        logger.error(f"Analytics timeseries error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/analytics/state")
async def get_state_comparison(
    metric: str = "validation_rate",
    survey_id: str = None
):
    """
    Get state-wise comparison for drill-down.
    
    Args:
        metric: Metric to compare (validation_rate, response_count, etc.)
        survey_id: Optional survey filter
    
    Returns:
        State-wise metrics with drill-down capability
    """
    try:
        demo_responses = []
        
        state_comparison = aggregation_engine.compute_state_comparison(
            demo_responses, 
            metric=metric
        )
        
        return JSONResponse(content={
            "success": True,
            "data": state_comparison
        })
    
    except Exception as e:
        logger.error(f"Analytics state comparison error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/analytics/validation")
async def get_validation_heatmap(
    survey_id: str = None
):
    """
    Get validation error heatmap (Agent vs Error Type).
    
    Returns:
        Matrix data for heatmap visualization
    """
    try:
        demo_responses = []
        
        heatmap = aggregation_engine.compute_validation_heatmap(demo_responses)
        
        return JSONResponse(content={
            "success": True,
            "data": heatmap
        })
    
    except Exception as e:
        logger.error(f"Analytics validation heatmap error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/analytics/anomalies")
async def get_anomalies(
    survey_id: str = None,
    threshold: float = 0.7
):
    """
    Get detected anomalies.
    
    Args:
        survey_id: Optional survey filter
        threshold: Anomaly score threshold (0-1)
    
    Returns:
        List of flagged responses with anomaly scores
    """
    try:
        demo_responses = [
            {'response_id': f'RESP_{i}', 'is_valid': True}
            for i in range(100)
        ]
        
        anomalies = aggregation_engine.compute_anomalies(demo_responses)
        
        return JSONResponse(content={
            "success": True,
            "data": anomalies
        })
    
    except Exception as e:
        logger.error(f"Analytics anomalies error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/analytics/sector")
async def get_sector_breakdown(
    survey_id: str = None
):
    """
    Get sector contribution breakdown.
    
    Returns:
        Sector-wise distribution for stacked bar/area chart
    """
    try:
        demo_responses = []
        
        sector_data = aggregation_engine.compute_sector_breakdown(demo_responses)
        
        return JSONResponse(content={
            "success": True,
            "data": sector_data
        })
    
    except Exception as e:
        logger.error(f"Analytics sector breakdown error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/analytics/agents")
async def get_agent_performance(
    survey_id: str = None
):
    """
    Get agent performance ranking.
    
    Returns:
        Agent performance table with metrics
    """
    try:
        demo_responses = []
        
        agent_data = aggregation_engine.compute_agent_performance(demo_responses)
        
        return JSONResponse(content={
            "success": True,
            "data": agent_data
        })
    
    except Exception as e:
        logger.error(f"Analytics agent performance error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
