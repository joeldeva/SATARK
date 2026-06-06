# SATARK.AI - Developer Notes

**Technical Documentation for Developers**

---

## 🏗️ Architecture Overview

SATARK.AI uses a **hybrid statistical intelligence architecture** combining:
1. Rule-based deterministic logic
2. Machine learning classification
3. Semantic embedding search
4. Statistical validation

### Core Philosophy
- **No LLM dependency**: Uses lightweight ML models only
- **Deterministic**: Same input → same output
- **Auditable**: Complete execution trace
- **Offline-first**: No external API calls

---

## 📁 Project Structure

```
satark_backend/
├── app.py                      # FastAPI application entry point
├── config.py                   # Configuration settings
├── requirements.txt            # Python dependencies
│
├── models/
│   └── survey_schema.py        # Pydantic models for API
│
├── core/                       # Core intelligence engines
│   ├── prompt_parser.py        # NLP-based prompt parsing
│   ├── domain_classifier.py    # ML domain classification
│   ├── retrieval_engine.py     # Semantic question retrieval
│   ├── survey_builder.py       # Deterministic survey construction
│   └── validation_engine.py    # Statistical validation
│
├── ml/                         # Machine learning components
│   ├── embeddings.py           # Embedding utilities
│   ├── anomaly_detector.py     # Response anomaly detection
│   └── embeddings/             # Cached embeddings
│       ├── question_vectors.faiss
│       └── questions_metadata.json
│
└── database/                   # Data storage
    ├── question_bank.json      # Official questions
    ├── routing_rules.json      # Skip logic rules
    └── coding_standards.json   # NCO/NIC/ISIC codes

frontend/
├── src/
│   ├── App.jsx                 # Main React application
│   ├── services/
│   │   └── api.js              # API client
│   └── components/
│       ├── PromptInput.jsx     # Prompt input component
│       ├── SurveyCanvas.jsx    # Survey editor
│       └── ValidationPanel.jsx # Validation display
└── package.json
```

---

## 🔧 Core Engines

### 1. Prompt Parser (`core/prompt_parser.py`)

**Purpose**: Extract structured intent from natural language prompts

**Technology**: spaCy NLP + regex + keyword extraction

**Input**:
```python
"Survey for rural women about healthcare access"
```

**Output**:
```python
PromptIntent(
    domain="health",
    audience="rural women",
    topic="healthcare access",
    keywords=["healthcare", "access", "rural", "women"],
    languages=["en"]
)
```

**Key Methods**:
- `parse(prompt: str) -> PromptIntent`: Main parsing method
- `_extract_domain(doc)`: Domain keyword extraction
- `_extract_audience(doc)`: Target audience identification
- `_extract_keywords(doc)`: Keyword extraction

**Dependencies**:
- spaCy (en_core_web_sm model)
- Python regex

---

### 2. Domain Classifier (`core/domain_classifier.py`)

**Purpose**: Classify survey domain using ML

**Technology**: TF-IDF + Logistic Regression

**Training Data**: Pre-labeled survey prompts

**Domains**: labour, health, agriculture, enterprise, education, household, demographic

**Key Methods**:
- `classify(prompt: str) -> str`: Classify domain
- `get_confidence(prompt: str) -> float`: Classification confidence
- `train(prompts, labels)`: Train classifier

**Model Storage**: Pickled scikit-learn models

---

### 3. Retrieval Engine (`core/retrieval_engine.py`)

**Purpose**: Semantic question retrieval using embeddings

**Technology**: SentenceTransformers + FAISS

**Model**: `sentence-transformers/all-MiniLM-L6-v2`

**Process**:
1. Load question bank
2. Generate embeddings for all questions
3. Create FAISS index for fast similarity search
4. Query with intent-based search string
5. Rank results by relevance

**Key Methods**:
- `retrieve_questions(intent, max_questions) -> List[Dict]`: Main retrieval
- `_create_embeddings()`: Generate embeddings
- `_matches_intent(question, intent) -> bool`: Filter by intent
- `_rank_questions(questions, intent) -> List[Dict]`: Rank by relevance

**Optimization**:
- Embeddings cached in FAISS index
- Lazy loading of SentenceTransformer model
- Fallback to keyword matching if embeddings fail

---

### 4. Survey Builder (`core/survey_builder.py`)

**Purpose**: Construct structured survey from retrieved questions

**Technology**: Pure Python rule-based logic

**Process**:
1. Add mandatory demographic questions
2. Convert retrieved questions to Question objects
3. Apply domain-specific rules
4. Remove duplicates
5. Order questions logically
6. Add routing logic
7. Create metadata

**Key Methods**:
- `build_survey(intent, questions, max_questions) -> Survey`: Main builder
- `_add_demographic_questions()`: Add demographics
- `_apply_domain_rules()`: Domain-specific logic
- `_order_questions()`: Logical ordering
- `_add_routing_logic()`: Skip logic

**Question Ordering**:
1. Demographic questions first
2. Core domain questions
3. Economic questions
4. Social questions
5. Follow-up questions

---

### 5. Validation Engine (`core/validation_engine.py`)

**Purpose**: Validate survey quality using statistical rules

**Technology**: Rule-based validation checks

**Checks**:
- Minimum question count (≥ 3)
- Maximum question count (≤ 50)
- Demographic coverage
- Question type distribution
- Routing logic validity
- Translation completeness

**Key Methods**:
- `validate_survey(survey) -> ValidationResult`: Main validation
- `_check_question_count()`: Count validation
- `_check_demographics()`: Demographic coverage
- `_check_routing()`: Skip logic validation

**Scoring**:
- Base score: 100
- Deduct points for each issue
- Minimum score: 0

---

### 6. Anomaly Detector (`ml/anomaly_detector.py`)

**Purpose**: Detect anomalies in survey responses

**Technology**: IsolationForest + Z-score

**Use Cases**:
- Speeding detection (too fast responses)
- Pattern duplication (copy-paste)
- Outlier detection (unusual values)
- Quality control

**Key Methods**:
- `detect_anomalies(responses) -> List[int]`: Detect anomalous responses
- `train(normal_responses)`: Train on normal data
- `get_anomaly_score(response) -> float`: Anomaly score

---

## 🔌 API Endpoints

### POST /generate-survey

**Request**:
```json
{
  "prompt": "Survey for rural women about healthcare",
  "languages": ["en", "hi"],
  "max_questions": 10,
  "domain": "health",
  "include_demographics": true
}
```

**Response**:
```json
{
  "success": true,
  "survey": {
    "survey_id": "uuid",
    "title": "Rural Women Healthcare Survey",
    "domain": "health",
    "questions": [...],
    "metadata": {...}
  },
  "intent": {
    "domain": "health",
    "audience": "rural women",
    "keywords": ["healthcare", "rural", "women"]
  },
  "validation_score": 93.8,
  "processing_time": 0.32,
  "engine_trace": [...]
}
```

**Processing Flow**:
```
Request → Prompt Parser → Domain Classifier → Retrieval Engine 
→ Survey Builder → Validation Engine → Response
```

---

## 🗄️ Data Models

### Survey Schema

```python
class Survey(BaseModel):
    survey_id: str
    title: str
    domain: SurveyDomain
    target_audience: Optional[str]
    languages: List[Language]
    questions: List[Question]
    metadata: SurveyMetadata
```

### Question Schema

```python
class Question(BaseModel):
    id: str
    text: MultilingualText
    type: QuestionType
    category: QuestionCategory
    required: bool
    options: Optional[List[AnswerOption]]
    validation: Optional[ValidationRule]
    routing: Optional[RoutingRule]
    standard_code: Optional[str]
    tags: List[str]
    source: Optional[str]
```

### Intent Schema

```python
class PromptIntent(BaseModel):
    domain: Optional[str]
    audience: Optional[str]
    topic: Optional[str]
    num_questions: Optional[int]
    keywords: List[str]
    languages: List[str]
    requirements: List[str]
    confidence: float
```

---

## 🧪 Testing

### Unit Tests

```bash
cd satark_backend
python test_satark.py
```

**Test Coverage**:
- Prompt parsing
- Domain classification
- Question retrieval
- Survey building
- Validation

### Integration Tests

```bash
# Test API endpoint
curl -X POST http://localhost:8000/generate-survey \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Test survey", "languages": ["en"], "max_questions": 5}'
```

### Performance Tests

```python
import time
start = time.time()
result = generate_survey(prompt)
print(f"Time: {time.time() - start:.2f}s")
```

**Target Performance**:
- Survey generation: < 0.5s
- Question retrieval: < 0.2s
- Validation: < 0.1s

---

## 🔄 Adding New Features

### Adding a New Domain

1. **Update Domain Enum** (`models/survey_schema.py`):
```python
class SurveyDomain(str, Enum):
    NEW_DOMAIN = "new_domain"
```

2. **Add Training Data** (`core/domain_classifier.py`):
```python
training_prompts.append("Survey about new domain topic")
training_labels.append("new_domain")
```

3. **Add Questions** (`database/question_bank.json`):
```json
{
  "id": "NEW_001",
  "domain": "new_domain",
  "text": {"en": "Question text"},
  ...
}
```

4. **Regenerate Embeddings**:
```bash
# Delete existing embeddings
rm satark_backend/ml/embeddings/*
# Restart server (will regenerate)
python app.py
```

### Adding a New Question

1. **Edit Question Bank** (`database/question_bank.json`):
```json
{
  "id": "UNIQUE_ID",
  "domain": "domain_name",
  "subdomain": "subdomain",
  "text": {
    "en": "English text",
    "hi": "Hindi text"
  },
  "type": "single_choice",
  "category": "core",
  "options": [...],
  "validation": {...},
  "tags": ["tag1", "tag2"],
  "source": "NSS",
  "standard_code": "CODE",
  "audience": ["all"]
}
```

2. **Regenerate Embeddings**:
```bash
rm satark_backend/ml/embeddings/*
python app.py
```

### Adding a New Language

1. **Update Language Enum** (`models/survey_schema.py`):
```python
class Language(str, Enum):
    NEW_LANG = "xx"  # ISO 639-1 code
```

2. **Add Translations** (`database/question_bank.json`):
```json
{
  "text": {
    "en": "English",
    "hi": "Hindi",
    "xx": "New language"
  }
}
```

3. **Update Frontend** (`frontend/src/components/PromptInput.jsx`):
```javascript
const languages = [
  { code: 'xx', name: 'New Language' }
];
```

---

## 🐛 Debugging

### Enable Debug Logging

```python
# In config.py
DEBUG = True
LOG_LEVEL = "DEBUG"
```

### View Engine Trace

Every API response includes `engine_trace`:
```json
{
  "engine_trace": [
    {
      "step": 1,
      "engine": "PromptParser",
      "method": "NLP + Rules",
      "output": "Intent extracted",
      "timestamp": "2026-02-06T14:30:00"
    }
  ]
}
```

### Common Issues

**Issue**: Embeddings not loading  
**Solution**: Delete `ml/embeddings/*` and restart

**Issue**: Domain misclassification  
**Solution**: Add more training examples in `domain_classifier.py`

**Issue**: No questions retrieved  
**Solution**: Check question bank has questions for that domain

**Issue**: Low validation score  
**Solution**: Check validation panel for specific errors

---

## 🚀 Deployment

### Production Checklist

- [ ] Set `DEBUG = False` in config.py
- [ ] Use production WSGI server (gunicorn)
- [ ] Enable HTTPS
- [ ] Set up monitoring
- [ ] Configure logging
- [ ] Backup question bank
- [ ] Test all domains
- [ ] Verify translations
- [ ] Load test API
- [ ] Document API changes

### Docker Deployment

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
RUN python -m spacy download en_core_web_sm

COPY . .
EXPOSE 8000

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Environment Variables

```bash
export SATARK_DEBUG=false
export SATARK_PORT=8000
export SATARK_HOST=0.0.0.0
export SATARK_LOG_LEVEL=INFO
```

---

## 📊 Performance Optimization

### Current Performance
- Survey generation: ~0.3s
- Question retrieval: ~0.15s
- Embedding search: ~0.05s
- Validation: ~0.02s

### Optimization Tips

1. **Cache Embeddings**: Already implemented with FAISS
2. **Lazy Load Models**: Load spaCy/transformers only when needed
3. **Batch Processing**: Process multiple surveys in parallel
4. **Database Indexing**: Use proper indexes for question lookup
5. **CDN for Frontend**: Serve static files from CDN

---

## 🔐 Security Considerations

### Current Security
- ✅ No external API calls
- ✅ Input validation with Pydantic
- ✅ CORS configured
- ✅ No SQL injection (JSON-based)
- ✅ No file uploads

### Recommendations
- Add rate limiting
- Implement authentication
- Add request logging
- Sanitize user inputs
- Use HTTPS in production

---

## 📚 Dependencies

### Backend
```
fastapi==0.104.1
uvicorn==0.24.0
pydantic==2.5.0
spacy==3.7.2
scikit-learn==1.3.2
sentence-transformers==2.2.2
faiss-cpu==1.7.4
numpy==1.26.2
pandas==2.1.3
```

### Frontend
```
react==18.2.0
@mui/material==5.14.18
axios==1.6.2
```

---

## 🎯 Future Enhancements

### Planned Features
1. **Advanced Routing**: Complex conditional logic
2. **Survey Templates**: Pre-built survey templates
3. **Collaborative Editing**: Multi-user editing
4. **Version Control**: Survey versioning
5. **Export Formats**: PDF, Excel, ODK, KoboToolbox
6. **Integration**: WhatsApp, IVR, SMS
7. **Analytics**: Survey response analytics
8. **Testing**: Survey pilot testing features

### Technical Debt
- Expand question bank to 200+ questions
- Add comprehensive unit tests
- Improve error handling
- Add request caching
- Optimize embedding generation

---

**Last Updated**: February 6, 2026  
**Maintainer**: SATARK.AI Development Team  
**Version**: 1.0.0
