# SATARK.AI - Quick Reference Card

**One-page reference for common tasks**

---

## 🚀 Quick Start

### Start System
```bash
# Terminal 1: Backend
cd satark_backend
python app.py

# Terminal 2: Frontend
cd frontend
npm start
```

### Access System
- **Web UI**: http://localhost:3000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

---

## 📝 Generate Survey (Web UI)

1. Open http://localhost:3000
2. Enter prompt: "Survey for [audience] about [topic]"
3. Select languages (EN, HI, etc.)
4. Set max questions (3-50)
5. Click "Generate Survey"
6. Review and edit questions
7. Export survey

---

## 🔌 Generate Survey (API)

```bash
curl -X POST http://localhost:8000/generate-survey \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Survey for rural women about healthcare",
    "languages": ["en", "hi"],
    "max_questions": 10
  }'
```

---

## 📊 Example Prompts

### Labour Survey
```
Survey for urban youth about employment and job satisfaction
```

### Health Survey
```
Survey for rural women about healthcare access and insurance
```

### Agriculture Survey
```
Survey for farmers about crop production and income
```

### Enterprise Survey
```
Survey for small business owners about operations and revenue
```

### Household Survey
```
Comprehensive household survey for income and asset assessment
```

---

## 🎯 Supported Domains

| Domain | Keywords | Example Topics |
|--------|----------|----------------|
| **Labour** | employment, job, work, occupation | Employment status, job satisfaction, income |
| **Health** | healthcare, medical, hospital | Healthcare access, insurance, satisfaction |
| **Agriculture** | farming, crops, land | Land ownership, crop production, income |
| **Enterprise** | business, company, enterprise | Business type, employees, revenue |
| **Education** | school, education, learning | Education level, barriers, access |
| **Household** | family, household, home | Household size, income, assets |
| **Demographic** | age, gender, location | Basic demographics (auto-included) |

---

## 🌐 Supported Languages

EN (English), HI (Hindi), BN (Bengali), TE (Telugu), TA (Tamil), MR (Marathi), GU (Gujarati), KN (Kannada), ML (Malayalam), OR (Odia), PA (Punjabi), AS (Assamese), UR (Urdu)

---

## ✅ Quality Indicators

| Score | Quality | Action |
|-------|---------|--------|
| 90-100% | Excellent | Ready to deploy |
| 80-89% | Good | Minor improvements |
| 70-79% | Fair | Review issues |
| < 70% | Poor | Significant changes needed |

---

## 🔧 Common Commands

### Check System Health
```bash
curl http://localhost:8000/health
```

### View System Info
```bash
curl http://localhost:8000/system-info
```

### Analyze Intent
```bash
curl -X POST http://localhost:8000/analyze-intent \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Your survey description"}'
```

### Run Tests
```bash
cd satark_backend
python test_satark.py
```

---

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| Backend not starting | Check port 8000 is free |
| Frontend not loading | Check port 3000 is free |
| No questions generated | Be more specific in prompt |
| Same questions always | Check question bank has domain questions |
| Low validation score | Check validation panel for errors |
| Slow performance | First request loads models (normal) |

---

## 📁 Important Files

| File | Purpose |
|------|---------|
| `satark_backend/app.py` | Main backend application |
| `satark_backend/database/question_bank.json` | Question repository |
| `frontend/src/App.jsx` | Main frontend application |
| `SYSTEM_STATUS.md` | System status report |
| `USER_GUIDE.md` | User documentation |
| `DEVELOPER_NOTES.md` | Technical documentation |

---

## 🎯 Quick Tips

### Writing Good Prompts
✅ **DO**: "Survey for rural women about healthcare access and insurance"  
❌ **DON'T**: "Make a survey"

### Question Count
- **Minimum**: 3 questions
- **Optimal**: 8-15 questions
- **Maximum**: 50 questions

### Languages
- Always include English (en)
- Add Hindi (hi) for wider reach
- Select based on target audience

### Validation
- Check validation score > 90%
- Review all errors before deployment
- Test survey with sample data

---

## 📞 Quick Links

- **System Status**: `SYSTEM_STATUS.md`
- **User Guide**: `USER_GUIDE.md`
- **Developer Notes**: `DEVELOPER_NOTES.md`
- **Session Summary**: `SESSION_SUMMARY.md`
- **Architecture**: `SATARK_ARCHITECTURE.md`

---

## 🔄 System Status

**Current Status**: ✅ OPERATIONAL

- Backend: ✅ Running (http://localhost:8000)
- Frontend: ✅ Running (http://localhost:3000)
- Question Bank: 22 questions
- Domains: 7 supported
- Languages: 13 supported
- Performance: 0.26s average
- Validation: 93.8% average

---

**Last Updated**: February 6, 2026  
**Version**: 1.0.0
