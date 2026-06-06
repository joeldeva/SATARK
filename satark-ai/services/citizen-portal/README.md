# Citizen Survey Interface - SATARK.AI

## Overview

A multilingual, multimodal citizen survey interface supporting:
- ✅ Web Interface
- ✅ WhatsApp Bot
- ✅ IVR System
- ✅ AI Avatar
- ✅ SMS/USSD

## Features

### 1. Identity Verification
- Aadhaar-linked OTP verification
- DigiLocker integration
- Face verification (optional)
- Mobile OTP fallback

### 2. Pre-Population Engine
- Auto-fill from past surveys
- Government dataset integration
- Location-based data
- Scheme eligibility detection

### 3. Adaptive Questioning
- Rule-based personalization
- ML-driven question flow
- Context-aware follow-ups
- Skip logic optimization

### 4. Multilingual Support
- 22 Indic languages + English
- IndicTrans2 translation
- Voice input/output
- Regional language UI

### 5. Real-Time Validation
- Rule-based checks
- ML anomaly detection
- Cross-agent conflict detection
- Instant feedback

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    User Channels                         │
├─────────────────────────────────────────────────────────┤
│  Web  │  WhatsApp  │  IVR  │  AI Avatar  │  SMS/USSD   │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│              Identity & Consent Layer                    │
│  • Aadhaar OTP  • DigiLocker  • Face Match              │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│              Pre-Population Engine                       │
│  • Past Surveys  • Gov Datasets  • Location Data        │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│              Adaptive Survey Engine                      │
│  • Rule Engine  • ML Classifier  • Skip Logic           │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│           Real-Time Validation Engine                    │
│  • Rules  • Anomaly Detection  • Conflict Check         │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│              Encrypted Data Store                        │
│  • PostgreSQL  • AES-256  • Audit Logs                  │
└─────────────────────────────────────────────────────────┘
```

## API Endpoints

### Authentication
- `POST /auth/initiate` - Initiate OTP verification
- `POST /auth/verify` - Verify OTP and get JWT token
- `POST /auth/face-verify` - Optional face verification

### Survey
- `GET /survey/{id}/prefill` - Get pre-populated data
- `GET /survey/{id}` - Get survey questions
- `POST /survey/{id}/submit` - Submit survey response
- `POST /survey/translate` - Translate survey to language

### Multimodal
- `POST /voice/transcribe` - Voice to text (Whisper)
- `POST /whatsapp/webhook` - WhatsApp message handler
- `POST /ivr/callback` - IVR DTMF handler
- `POST /avatar/generate` - Generate AI avatar video

### Validation
- `POST /validate/realtime` - Real-time validation
- `GET /validate/conflicts` - Check for conflicts

## Tech Stack

### Backend
- FastAPI (Python 3.11+)
- PostgreSQL (data storage)
- Redis (caching, sessions)
- Celery (async tasks)

### ML/AI
- IndicTrans2 (translation)
- Whisper (speech-to-text)
- InsightFace (face verification)
- scikit-learn (adaptive logic)

### Frontend
- React 18
- Tailwind CSS
- React Query
- Zustand (state management)

### Integrations
- WhatsApp Business API
- Twilio (SMS, WhatsApp)
- Exotel (IVR)
- DigiLocker API

## Security

- AES-256 encryption at rest
- TLS 1.3 in transit
- JWT authentication
- Field-level encryption for PII
- No raw Aadhaar storage
- Audit logging
- DPDP Act compliant

## Quick Start

```bash
# Install dependencies
cd services/citizen-portal
pip install -r requirements.txt
npm install

# Set environment variables
cp .env.example .env

# Run backend
uvicorn app:app --reload --port 8004

# Run frontend
npm run dev
```

## Testing

```bash
# Run tests
pytest tests/

# Test OTP flow
curl -X POST http://localhost:8004/auth/initiate \
  -H "Content-Type: application/json" \
  -d '{"mobile_number": "9876543210"}'

# Test survey prefill
curl -X GET http://localhost:8004/survey/PLFS_001/prefill \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Deployment

See [DEPLOYMENT.md](./DEPLOYMENT.md) for production deployment instructions.
