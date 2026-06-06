# SATARK.AI - Deterministic Survey Intelligence Engine

## 🎯 **CORE PHILOSOPHY**
**SATARK.AI is NOT a chatbot.** It's a hybrid statistical intelligence system that combines:
- **Rule Engine** (Primary logic)
- **Question Repository** (Official source)
- **NLP Classifier** (Intent detection)
- **Embedding Search** (Semantic retrieval)
- **Statistical ML** (Validation)
- **Optional Small LLM** (Only for rephrasing/summarizing)

## 🏗️ **SYSTEM ARCHITECTURE**

```
User Prompt
    ↓
Prompt Parser (NLP + Rules)
    ↓
Intent Object
    ↓
Question Retrieval Engine (DB + Embeddings)
    ↓
Survey Structuring Engine (Rules + Templates)
    ↓
Validation Rules Injection
    ↓
Final Survey JSON
    ↓
Deployment (Agent / WhatsApp / IVR)
```

**No hallucination anywhere. Fully deterministic. Completely auditable.**

## 📁 **PROJECT STRUCTURE**

```
satark_backend/
│
├── app.py                      # FastAPI main application
├── config.py                   # Configuration settings
├── requirements.txt            # Dependencies
│
├── models/                     # Data schemas
│   ├── survey_schema.py        # Survey structure definitions
│   ├── question_schema.py      # Question format specifications
│   └── response_schema.py      # API response models
│
├── core/                       # Core intelligence engines
│   ├── prompt_parser.py        # NLP-based intent extraction
│   ├── domain_classifier.py    # ML domain classification
│   ├── retrieval_engine.py     # Embedding-based question retrieval
│   ├── survey_builder.py       # Deterministic survey assembly
│   ├── validation_engine.py    # Rule-based validation
│   └── coding_engine.py        # NCO/NIC/ISIC auto-coding
│
├── ml/                         # Machine learning components
│   ├── embeddings.py           # Sentence transformer embeddings
│   ├── anomaly_detector.py     # Response pattern analysis
│   └── domain_model.py         # Trained classification models
│
├── database/                   # Official data repositories
│   ├── question_bank.json      # NSS/NFHS/PLFS questions
│   ├── routing_rules.json      # Survey logic templates
│   ├── coding_standards.json   # NCO/NIC/ISIC mappings
│   └── validation_rules.json   # Field validation specifications
│
└── api/                        # API endpoints
    ├── survey_routes.py         # Survey generation endpoints
    ├── validation_routes.py     # Validation endpoints
    └── analytics_routes.py      # Quality analytics
```

## 🔷 **CORE COMPONENTS**

### **1. Official Question Repository**
- **Source**: Real NSS schedules, PLFS forms, NFHS questionnaires, ASI forms
- **Format**: Structured JSON with metadata
- **Features**: Domain tagging, audience targeting, validation rules

### **2. Prompt Parser Engine**
- **Technology**: spaCy + regex + keyword mapping
- **Output**: Structured intent object
- **No LLM**: Pure NLP and rule-based extraction

### **3. Domain Classification**
- **Technology**: scikit-learn TF-IDF + Logistic Regression
- **Training**: Sample prompts labeled by domain
- **Benefit**: Explainable classification

### **4. Embedding-Based Retrieval**
- **Model**: sentence-transformers/all-MiniLM-L6-v2
- **Storage**: FAISS vector database
- **Purpose**: Semantic question matching without hallucination

### **5. Survey Builder Engine**
- **Logic**: Deterministic rule-based assembly
- **Features**: Mandatory blocks, logical ordering, skip logic
- **Output**: Structured survey JSON

### **6. Validation Engine**
- **Type**: Pure Python logic rules
- **Checks**: Range, required fields, cross-field consistency
- **Standards**: MoSPI compliance validation

### **7. Anomaly Detection**
- **Technology**: IsolationForest, Z-score, IQR methods
- **Purpose**: Response quality monitoring
- **Target**: Speeding agents, pattern duplication

### **8. Auto-Coding Engine**
- **Method**: Keyword matching + embedding similarity
- **Standards**: NCO/NIC/ISIC mappings
- **Approach**: Structured mapping, not generative

## 🎯 **STRATEGIC POSITIONING**

### **Government Presentation Statement:**
*"SATARK.AI does not rely on uncontrolled generative AI. It uses a hybrid statistical intelligence architecture — combining official question repositories, deterministic rule engines, semantic retrieval, and lightweight ML models — ensuring auditability and statistical integrity."*

### **Key Advantages:**
- ✅ **Deterministic**: No random outputs
- ✅ **Cheaper**: No expensive LLM API calls
- ✅ **Offline-ready**: Works without internet
- ✅ **Explainable**: Every decision traceable
- ✅ **Government-safe**: Meets PS requirements
- ✅ **Auditable**: Full process transparency

## 🔁 **DATA FLOW**

1. **Officer types prompt** → Natural language input
2. **Prompt Parser extracts intent** → Structured object
3. **Domain classifier confirms domain** → ML classification
4. **Embedding search retrieves questions** → Semantic matching
5. **Survey Builder assembles form** → Rule-based construction
6. **Validation engine injects rules** → Compliance checking
7. **Final survey JSON returned** → Deployment-ready output

## 🏆 **TECHNICAL SUPERIORITY**

### **vs Pure LLM Approaches:**
- **No hallucination risk**
- **Consistent output quality**
- **Lower computational cost**
- **Better regulatory compliance**
- **Transparent decision making**
- **Offline capability**

### **vs Traditional Survey Tools:**
- **AI-powered intent understanding**
- **Semantic question matching**
- **Automated compliance checking**
- **Multi-language support**
- **Real-time validation**
- **Statistical quality monitoring**

## 📊 **QUALITY ASSURANCE**

### **Built-in Safeguards:**
- Official question repository validation
- Rule-based logic verification
- Statistical anomaly detection
- Cross-field consistency checking
- MoSPI standard compliance
- Audit trail generation

### **Performance Monitoring:**
- Response time tracking
- Question relevance scoring
- Validation rule effectiveness
- User satisfaction metrics
- System reliability monitoring

This architecture ensures **SATARK.AI** delivers government-grade survey intelligence while maintaining the flexibility and efficiency needed for modern survey operations.