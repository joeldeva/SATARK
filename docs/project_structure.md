# Project Structure

```
ai-survey-generator/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                    # FastAPI app entry point
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── survey.py              # Survey data models
│   │   │   └── prompt.py              # Prompt parsing models
│   │   ├── engines/
│   │   │   ├── __init__.py
│   │   │   ├── prompt_parser.py       # NLP prompt understanding
│   │   │   ├── rule_engine.py         # Deterministic rules
│   │   │   ├── rag_engine.py          # Question retrieval
│   │   │   └── survey_builder.py      # Survey construction
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   └── routes.py              # API endpoints
│   │   └── utils/
│   │       ├── __init__.py
│   │       ├── validators.py          # Survey validation
│   │       └── coding.py              # Auto-coding (NCO/NIC)
│   ├── requirements.txt
│   └── config.py
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── components/
│   │   │   ├── PromptInput.jsx        # Prompt entry interface
│   │   │   ├── SurveyCanvas.jsx       # Survey editor
│   │   │   └── ValidationPanel.jsx    # Standards checker
│   │   ├── services/
│   │   │   └── api.js                 # Backend communication
│   │   └── App.jsx
│   ├── package.json
│   └── package-lock.json
├── knowledge_base/
│   ├── questions/
│   │   ├── labour_questions.json      # NSS labour questions
│   │   ├── health_questions.json      # NFHS health questions
│   │   └── demographic_questions.json # Standard demographics
│   ├── standards/
│   │   ├── mospi_guidelines.json      # MoSPI standards
│   │   ├── gsbpm_phases.json          # GSBPM compliance
│   │   └── coding_standards.json      # NCO/NIC/ISIC codes
│   └── embeddings/
│       └── question_vectors.faiss     # Vector store for RAG
├── schemas/
│   ├── survey_schema.json             # Standard survey format
│   └── validation_rules.json          # Validation specifications
└── README.md
```