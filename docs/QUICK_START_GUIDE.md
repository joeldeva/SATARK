# SATARK.AI - Quick Start Guide for Developers

## 🚀 Get Started in 5 Minutes

### Current System Status
- ✅ Backend: Running on http://localhost:8000
- ✅ Frontend: Running on http://localhost:3000
- ✅ Question Bank: 22 questions across 8 domains
- ✅ Embeddings: Generated and indexed in FAISS

---

## 📋 Prerequisites Checklist

```bash
# Check Python version (need 3.13+)
python --version

# Check Node.js version (need 18+)
node --version

# Check npm
npm --version
```

---

## 🔧 Installation (First Time)

### Step 1: Backend Setup
```bash
cd satark_backend

# Install dependencies
pip install -r requirements.txt

# Download spaCy model
python -m spacy download en_core_web_sm

# Verify installation
python -c "import fastapi; import sentence_transformers; import spacy; print('✅ All dependencies installed')"
```

### Step 2: Frontend Setup
```bash
cd frontend

# Install dependencies
npm install

# Verify installation
npm list react
```

---

## ▶️ Running the System

### Option 1: Manual Start (Recommended for Development)

**Terminal 1 - Backend:**
```bash
cd satark_backend
python app.py
```
Wait for: `✅ All SATARK.AI engines initialized successfully`

**Terminal 2 - Frontend:**
```bash
cd frontend
npm start
```
Wait for: `webpack compiled successfully`

### Option 2: Using Batch Files (Windows)

**Backend:**
```bash
run_backend.bat
```

**Frontend:**
```bash
run_frontend.bat
```

---

## 🧪 Testing the System

### 1. Health Check
```bash
curl http://localhost:8000/health
```

**Expected Response:**
```json
{
  "status": "healthy",
  "engines": {
    "prompt_parser": true,
    "domain_classifier": true,
    "retrieval_engine": true,
    "survey_builder": true,
    "validation_engine": true,
    "anomaly_detector": true
  }
}
```

### 2. Generate a Survey (PowerShell)
```powershell
$headers = @{'Content-Type' = 'application/json'}
$body = '{"prompt": "Survey for rural women about healthcare access", "languages": ["en"], "max_questions": 10}'
$result = Invoke-RestMethod -Uri "http://localhost:8000/generate-survey" -Method POST -Body $body -Headers $headers
$result.survey.questions | ForEach-Object { Write-Host "- $($_.text.en)" }
```

### 3. Test Different Domains

**Labour Survey:**
```json
{
  "prompt": "Survey for urban youth about employment and job satisfaction",
  "languages": ["en"],
  "max_questions": 10
}
```

**Health Survey:**
```json
{
  "prompt": "Survey for rural women about healthcare access and insurance",
  "languages": ["en"],
  "max_questions": 10
}
```

**Agriculture Survey:**
```json
{
  "prompt": "Survey for farmers about crop production and income",
  "languages": ["en"],
  "max_questions": 10
}
```

**Enterprise Survey:**
```json
{
  "prompt": "Survey for small business owners about enterprise operations",
  "languages": ["en"],
  "max_questions": 10
}
```

---

## 📂 Key Files to Know

### Backend Files
```
satark_backend/
├── app.py                          # Main entry point - START HERE
├── config.py                       # Configuration settings
├── models/survey_schema.py         # Data models (Pydantic)
├── core/
│   ├── prompt_parser.py            # Extracts intent from prompt
│   ├── domain_classifier.py        # Classifies survey domain
│   ├── retrieval_engine.py         # Finds relevant questions
│   ├── survey_builder.py           # Builds final survey
│   └── validation_engine.py        # Validates survey quality
├── ml/
│   ├── anomaly_detector.py         # Detects anomalies
│   └── embeddings/                 # FAISS vector index
└── database/
    └── question_bank.json          # All questions - EDIT THIS TO ADD QUESTIONS
```

### Frontend Files
```
frontend/
├── src/
│   ├── App.jsx                     # Main React component
│   ├── components/
│   │   ├── PromptInput.jsx         # Where user types prompt
│   │   ├── SurveyCanvas.jsx        # Shows generated survey
│   │   └── ValidationPanel.jsx     # Shows validation results
│   └── services/
│       └── api.js                  # API calls to backend
```

---

## 🔨 Common Development Tasks

### Task 1: Add New Questions to Question Bank

**File:** `satark_backend/database/question_bank.json`

```json
{
  "id": "NEW_001",
  "domain": "labour",
  "subdomain": "wages",
  "text": {
    "en": "What is your hourly wage rate?",
    "hi": "आपकी प्रति घंटा मजदूरी दर क्या है?"
  },
  "type": "number",
  "category": "economic",
  "validation": {
    "min_value": 0,
    "max_value": 10000,
    "required": false
  },
  "tags": ["wages", "hourly", "labour", "income"],
  "source": "PLFS",
  "standard_code": "LAB_WAGE_HOURLY",
  "audience": ["employed", "daily_wage"]
}
```

**After adding questions:**
1. Delete embeddings: `satark_backend/ml/embeddings/question_vectors.faiss`
2. Delete metadata: `satark_backend/ml/embeddings/questions_metadata.json`
3. Restart backend - embeddings will regenerate automatically

### Task 2: Modify Survey Generation Logic

**File:** `satark_backend/core/survey_builder.py`

Key methods:
- `build_survey()` - Main entry point
- `_add_demographic_questions()` - Add mandatory demographics
- `_apply_domain_rules()` - Domain-specific logic
- `_order_questions()` - Question ordering

### Task 3: Change Validation Rules

**File:** `satark_backend/core/validation_engine.py`

Key methods:
- `validate_survey()` - Main validation
- `_check_question_quality()` - Question-level checks
- `_check_routing_logic()` - Skip logic validation

### Task 4: Adjust Domain Classification

**File:** `satark_backend/core/domain_classifier.py`

Training data is in `_get_training_data()` method. Add more examples to improve accuracy.

---

## 🐛 Troubleshooting

### Problem: Backend won't start

**Error:** `ModuleNotFoundError: No module named 'fastapi'`

**Solution:**
```bash
cd satark_backend
pip install -r requirements.txt
```

### Problem: spaCy model not found

**Error:** `Can't find model 'en_core_web_sm'`

**Solution:**
```bash
python -m spacy download en_core_web_sm
```

### Problem: Frontend won't compile

**Error:** `Module not found: Can't resolve '@mui/material'`

**Solution:**
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
```

### Problem: Same questions for all surveys

**Solution:** This was fixed! Make sure you have the latest code with:
- 22+ questions in question_bank.json
- Updated retrieval_engine.py with flexible matching
- Regenerated embeddings

### Problem: Port already in use

**Error:** `Address already in use: 8000`

**Solution:**
```bash
# Windows
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Or change port in config.py
API_PORT = 8001
```

---

## 📊 Understanding the Data Flow

```
1. User types prompt in frontend
   ↓
2. Frontend sends POST to /generate-survey
   ↓
3. Backend: Prompt Parser extracts intent
   - Domain: "health"
   - Audience: "rural women"
   - Keywords: ["healthcare", "access"]
   ↓
4. Backend: Domain Classifier confirms domain
   - Uses TF-IDF + Logistic Regression
   - Returns confidence score
   ↓
5. Backend: Retrieval Engine finds questions
   - Embeds intent using SentenceTransformers
   - Searches FAISS index
   - Returns top-k relevant questions
   ↓
6. Backend: Survey Builder constructs survey
   - Adds mandatory demographics
   - Adds domain-specific questions
   - Orders questions logically
   - Adds validation rules
   ↓
7. Backend: Validation Engine checks quality
   - Range checks
   - Logic consistency
   - Routing validation
   ↓
8. Backend: Returns survey JSON
   ↓
9. Frontend: Displays survey in SurveyCanvas
```

---

## 🎯 Next Development Priorities

### Immediate (This Week)
1. **Expand question bank to 50 questions**
   - Add 10 more labour questions
   - Add 8 more health questions
   - Add 5 more agriculture questions
   - Add 5 more enterprise questions

2. **Improve domain classification**
   - Add more training examples
   - Test with edge cases

3. **Enhance validation**
   - Add cross-field validation
   - Improve error messages

### Short-term (Next 2 Weeks)
1. **Admin dashboard**
   - Real-time survey stats
   - Question usage analytics
   - Error tracking

2. **Paradata tracking**
   - Response time tracking
   - Enumerator metrics

3. **Layer 3 validation**
   - Integrate Phi-3-mini
   - Coherence checking

---

## 📚 Useful Commands

### Backend Development
```bash
# Run with auto-reload
cd satark_backend
uvicorn app:app --reload --host 0.0.0.0 --port 8000

# Run tests
python test_satark.py

# Check code style
flake8 .

# Format code
black .
```

### Frontend Development
```bash
# Run development server
npm start

# Build for production
npm run build

# Run tests
npm test

# Check for updates
npm outdated
```

### Database Operations
```bash
# Validate question bank JSON
python -m json.tool satark_backend/database/question_bank.json

# Count questions
python -c "import json; data=json.load(open('satark_backend/database/question_bank.json')); print(f'{len(data)} questions')"

# List domains
python -c "import json; data=json.load(open('satark_backend/database/question_bank.json')); domains=set(q['domain'] for q in data); print(domains)"
```

---

## 🔗 Important URLs

- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Frontend**: http://localhost:3000
- **Health Check**: http://localhost:8000/health
- **System Info**: http://localhost:8000/system-info

---

## 💡 Pro Tips

1. **Use API docs for testing**: http://localhost:8000/docs has interactive API testing
2. **Check engine trace**: Every survey response includes `engine_trace` showing exactly what happened
3. **Monitor logs**: Backend logs show detailed processing steps
4. **Use validation_score**: Surveys with score <80% may need review
5. **Test with different prompts**: Try various phrasings to improve intent parsing

---

## 🎓 Learning Resources

- **FastAPI**: https://fastapi.tiangolo.com/
- **React**: https://react.dev/
- **SentenceTransformers**: https://www.sbert.net/
- **FAISS**: https://github.com/facebookresearch/faiss
- **MoSPI Standards**: https://mospi.gov.in
- **GSBPM**: https://statswiki.unece.org/display/GSBPM

---

**Happy Coding! 🚀**

For detailed architecture and roadmap, see:
- [SATARK_ARCHITECTURE.md](SATARK_ARCHITECTURE.md)
- [SURVEY_INTELLIGENCE_ROADMAP.md](SURVEY_INTELLIGENCE_ROADMAP.md)
- [PHASE2_IMPLEMENTATION_PLAN.md](PHASE2_IMPLEMENTATION_PLAN.md)
