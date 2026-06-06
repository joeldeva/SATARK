# AI Survey Generator - Implementation Guide

## 🎯 System Overview

This is a **hybrid AI system** that generates GSBPM-compliant, MoSPI-standard surveys from simple text prompts. The system combines:

- **Rule Engine**: Fast, deterministic logic for mandatory requirements
- **RAG Engine**: Retrieval of official government questions from knowledge base
- **Optional LLM**: Small local model for refinement (not implemented in this version)
- **Validation Engine**: Ensures compliance with standards

## 🏗️ Architecture

```
Frontend (React)
    ↓ HTTP/JSON
Backend API (FastAPI)
    ↓
Prompt Parser (spaCy + Rules)
    ↓
┌─────────────────────────────────┐
│  Hybrid Generation Engine      │
│  ├── Rule Engine (Primary)     │
│  ├── RAG Engine (Knowledge)    │
│  └── LLM Engine (Optional)     │
└─────────────────────────────────┘
    ↓
Survey Builder & Validator
    ↓
JSON Output (Deployment Ready)
```

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Node.js 16+
- npm or yarn

### Installation

1. **Clone and setup:**
```bash
git clone <repository>
cd ai-survey-generator
python setup.py
```

2. **Start backend:**
```bash
python run_backend.py
# Or on Windows: run_backend.bat
```

3. **Start frontend:**
```bash
cd frontend
npm start
# Or on Windows: run_frontend.bat
```

4. **Access application:**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs

## 📋 Usage Examples

### Example 1: Basic Labour Survey
**Prompt:** "A survey for rural women about access to healthcare with 8 questions, include income and satisfaction"

**Generated Output:**
- Domain: health
- Target: rural women  
- Questions: 8 (3 demographics + 5 health-specific)
- Languages: English, Hindi
- Standard: NFHS compliant

### Example 2: Employment Survey
**Prompt:** "Employment survey for urban youth aged 18-25, focus on job satisfaction and career goals"

**Generated Output:**
- Domain: labour
- Target: urban youth
- Questions: 10 (3 demographics + 7 employment)
- Includes: NCO occupation coding
- Standard: PLFS compliant

### Example 3: Multilingual Survey
**Prompt:** "Health insurance awareness survey for elderly population in Hindi and English"

**Generated Output:**
- Domain: health
- Languages: English + Hindi translations
- Age-appropriate questions
- Insurance-focused content

## 🔧 System Components

### 1. Prompt Parser (`backend/app/engines/prompt_parser.py`)
- **Input**: Natural language prompt
- **Processing**: spaCy NLP + regex patterns
- **Output**: Structured intent object

**Key Features:**
- Domain detection (labour, health, education, etc.)
- Audience extraction (rural women, urban youth, etc.)
- Language detection
- Question count extraction
- Special requirements parsing

### 2. Rule Engine (`backend/app/engines/rule_engine.py`)
- **Purpose**: Deterministic survey generation
- **Functions**:
  - Mandatory demographic questions
  - Domain-specific rules
  - Validation rule application
  - Question ordering

**Domain Rules:**
- **Labour**: Employment status, occupation (NCO codes), income
- **Health**: Health status, facility access, insurance
- **Education**: Literacy, education level, enrollment
- **Agriculture**: Land ownership, crops, irrigation
- **Household**: Family size, housing, assets
- **Enterprise**: Business type, employment size, turnover

### 3. RAG Engine (`backend/app/engines/rag_engine.py`)
- **Purpose**: Retrieve relevant questions from knowledge base
- **Technology**: Sentence Transformers + FAISS vector search
- **Knowledge Base**: 
  - Official NSS questions
  - NFHS health questions
  - Standard demographic questions
  - MoSPI guidelines

**Process:**
1. Convert intent to search query
2. Generate embeddings using SentenceTransformers
3. Search FAISS index for similar questions
4. Filter by domain, audience, language
5. Rank by relevance score

### 4. Survey Builder (`backend/app/engines/survey_builder.py`)
- **Purpose**: Orchestrate all engines to build final survey
- **Process**:
  1. Generate mandatory questions (Rule Engine)
  2. Retrieve relevant questions (RAG Engine)
  3. Combine and deduplicate
  4. Apply domain rules
  5. Add validation rules
  6. Order questions properly
  7. Create routing logic
  8. Generate metadata

### 5. Frontend Components

#### PromptInput (`frontend/src/components/PromptInput.jsx`)
- Natural language prompt entry
- Domain and language selection
- Question count slider
- Example prompts
- Real-time validation

#### SurveyCanvas (`frontend/src/components/SurveyCanvas.jsx`)
- Generated survey display
- Question editing interface
- JSON view toggle
- Drag-and-drop reordering
- Multilingual text display

#### ValidationPanel (`frontend/src/components/ValidationPanel.jsx`)
- GSBPM compliance checking
- MoSPI standards validation
- Accessibility assessment
- Deployment readiness
- Compliance scoring

## 📊 Knowledge Base Structure

### Question Files
```
knowledge_base/questions/
├── labour_questions.json      # Employment, occupation, income
├── health_questions.json      # Healthcare access, satisfaction
├── demographic_questions.json # Age, gender, location, education
└── [domain]_questions.json    # Additional domains
```

### Question Format
```json
{
  "id": "LAB_001",
  "domain": "labour",
  "category": "employment_status",
  "question": {
    "en": "What is your current employment status?",
    "hi": "आपकी वर्तमान रोजगार स्थिति क्या है?"
  },
  "type": "single_choice",
  "options": [...],
  "standard": "PLFS",
  "keywords": ["employment", "job", "work"],
  "audience": ["all"],
  "required": true,
  "routing": {
    "show_if": "age >= 15"
  }
}
```

### Standards Files
```
knowledge_base/standards/
├── mospi_guidelines.json      # MoSPI survey standards
├── gsbpm_phases.json         # GSBPM compliance rules
└── coding_standards.json     # NCO/NIC/ISIC codes
```

## 🔍 Validation & Compliance

### GSBPM Compliance
- **Design Phase**: Survey structure, metadata
- **Build Phase**: Question validation, routing logic
- **Collect Phase**: Deployment readiness
- **Process Phase**: Data validation rules
- **Analyse Phase**: Standard coding support
- **Disseminate Phase**: Export formats

### MoSPI Standards
- **Domain Classification**: Proper categorization
- **Question Coding**: NCO/NIC/ISIC standards
- **Demographic Requirements**: Mandatory fields
- **Language Support**: Regional languages
- **Accessibility**: Mobile-friendly design

### Quality Checks
- Question count (3-50 range)
- Demographic questions first
- Proper validation rules
- Multilingual consistency
- Mobile compatibility
- Standard code mapping

## 🚀 Deployment Options

### 1. Web Application
- Responsive React frontend
- RESTful API backend
- Real-time validation
- JSON export

### 2. WhatsApp Integration
- Conversational survey flow
- Voice message support
- Image question support
- Progress tracking

### 3. IVR System
- Voice-based surveys
- DTMF input handling
- Multi-language support
- Call routing logic

### 4. Mobile App
- Offline capability
- GPS location capture
- Photo attachments
- Sync when online

## 🔧 Configuration

### Backend Configuration (`backend/config.py`)
```python
# API Settings
API_HOST = "0.0.0.0"
API_PORT = 8000

# Survey Limits
MAX_QUESTIONS = 50
MIN_QUESTIONS = 3

# RAG Settings
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
TOP_K_QUESTIONS = 20

# Languages
SUPPORTED_LANGUAGES = ["en", "hi", "bn", "te", "ta", "mr", "gu", "kn", "ml", "or"]
```

### Frontend Configuration (`frontend/package.json`)
```json
{
  "proxy": "http://localhost:8000",
  "dependencies": {
    "react": "^18.2.0",
    "@mui/material": "^5.11.0",
    "axios": "^1.6.0"
  }
}
```

## 🧪 Testing

### Backend Tests
```bash
cd backend
python -m pytest tests/
```

### Frontend Tests
```bash
cd frontend
npm test
```

### Integration Tests
```bash
python tests/integration_test.py
```

## 📈 Performance Optimization

### Backend Optimizations
- **Caching**: Redis for frequent queries
- **Database**: PostgreSQL for survey storage
- **Async**: FastAPI async endpoints
- **Compression**: Gzip response compression

### Frontend Optimizations
- **Code Splitting**: React.lazy loading
- **Caching**: Service worker caching
- **Bundling**: Webpack optimization
- **CDN**: Static asset delivery

### RAG Optimizations
- **Vector Index**: FAISS GPU acceleration
- **Model**: Quantized embedding models
- **Caching**: Embedding result caching
- **Batch Processing**: Bulk question processing

## 🔒 Security Considerations

### Data Privacy
- **No External APIs**: All processing local
- **No Data Storage**: Stateless processing
- **Encryption**: HTTPS/TLS encryption
- **Anonymization**: PII removal from logs

### API Security
- **Rate Limiting**: Request throttling
- **Input Validation**: Pydantic models
- **CORS**: Controlled cross-origin requests
- **Authentication**: JWT tokens (optional)

## 🛠️ Extending the System

### Adding New Domains
1. Create question file: `knowledge_base/questions/[domain]_questions.json`
2. Add domain rules: `backend/app/engines/rule_engine.py`
3. Update configuration: `backend/config.py`
4. Regenerate embeddings: Delete `knowledge_base/embeddings/`

### Adding New Languages
1. Update language list: `backend/config.py`
2. Add translations to question files
3. Update frontend language selector
4. Test multilingual generation

### Adding LLM Integration
1. Install LLM library (e.g., `transformers`, `ollama`)
2. Create LLM engine: `backend/app/engines/llm_engine.py`
3. Integrate with survey builder
4. Add LLM configuration options

### Custom Validation Rules
1. Add rules to: `knowledge_base/standards/validation_rules.json`
2. Update validator: `backend/app/utils/validators.py`
3. Add frontend validation display

## 🐛 Troubleshooting

### Common Issues

**1. spaCy Model Not Found**
```bash
python -m spacy download en_core_web_sm
```

**2. FAISS Installation Issues**
```bash
pip install faiss-cpu  # For CPU-only
# OR
pip install faiss-gpu  # For GPU support
```

**3. Frontend Build Errors**
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
```

**4. Backend Import Errors**
```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)/backend"
```

### Performance Issues

**1. Slow Question Retrieval**
- Check FAISS index exists: `knowledge_base/embeddings/`
- Regenerate embeddings if corrupted
- Consider GPU acceleration for large knowledge bases

**2. High Memory Usage**
- Use quantized embedding models
- Implement result caching
- Batch process large requests

### Debugging

**1. Enable Debug Mode**
```python
# backend/config.py
DEBUG = True
```

**2. Check Logs**
```bash
tail -f backend/logs/app.log
```

**3. API Testing**
```bash
curl -X POST http://localhost:8000/generate-survey \
  -H "Content-Type: application/json" \
  -d '{"prompt": "test survey", "max_questions": 5}'
```

## 📚 Additional Resources

### Standards Documentation
- [GSBPM Framework](https://statswiki.unece.org/display/GSBPM)
- [MoSPI Guidelines](http://mospi.nic.in/)
- [NSS Methodology](http://www.mospi.gov.in/nss)

### Technical Documentation
- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [React Documentation](https://reactjs.org/docs/)
- [Material-UI Components](https://mui.com/)
- [Sentence Transformers](https://www.sbert.net/)

### Survey Design Best Practices
- [Survey Methodology](https://www.pewresearch.org/methods/)
- [Question Design Guidelines](https://www.questionpro.com/blog/survey-question-design/)
- [Cross-Cultural Survey Guidelines](https://ccsg.isr.umich.edu/)

## 🤝 Contributing

### Development Setup
1. Fork the repository
2. Create feature branch: `git checkout -b feature/new-feature`
3. Make changes and test
4. Submit pull request

### Code Standards
- **Python**: PEP 8, type hints, docstrings
- **JavaScript**: ESLint, Prettier formatting
- **Documentation**: Markdown with examples
- **Testing**: Unit tests for new features

### Issue Reporting
- Use GitHub issues
- Include system information
- Provide reproduction steps
- Add relevant logs/screenshots

---

**Built with ❤️ for Government Survey Excellence**

*This system ensures no data leaks, maintains open-source transparency, and provides audit trails for all survey generation processes.*