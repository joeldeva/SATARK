# SATARK - Survey Intelligence Platform
**सतर्क** | Survey Analysis, Tracking And Response Knowledge  
*"Vigilant Data Collection for Vigilant India"*

## Quick Start

```bash
cd backend
pip install -r requirements.txt
python main.py
```

API runs at: http://localhost:8001  
Docs: http://localhost:8001/docs

## Generate a Survey

```bash
curl -X POST http://localhost:8001/api/v1/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "A survey for rural women about healthcare access with 8 questions"}'
```

## Architecture
- Prompt Parser → NLP intent extraction
- RAG Engine → SentenceTransformers + ChromaDB (keyword fallback)
- Rule Engine → Mandatory questions, ordering, validation
- Survey Generator → Combines all three into final JSON
