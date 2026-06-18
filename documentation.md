# SATARK API, Channel, and Export Documentation

This file documents the working end-to-end flow:

1. Create and publish a survey in **Survey Design**.
2. Deploy it in **Field Operation**.
3. Collect data in **Enumerator Client** or through WhatsApp / IVR / avatar channels.
4. Validate answers in real time.
5. Capture paradata and monitor quality.
6. Download the final national report CSV.

## Environment Setup

Do not commit real API keys. Keep secrets in local environment files.

Frontend:

```env
# apps/web/.env.local
VITE_API_URL=/api
VITE_GOOGLE_TRANSLATE_API_KEY=<google-translate-api-key>
```

Backend:

```env
# apps/api/.env
ENVIRONMENT=development
DEBUG=true
DATABASE_URL=postgresql+psycopg://satark:satark@127.0.0.1:5432/satark
KNOWLEDGE_BASE_PATH=../../data
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,http://127.0.0.1:3001
SECRET_KEY=<strong-local-secret>
REDIS_URL=redis://127.0.0.1:6379/0
VECTOR_STORE=auto
CHROMA_DIR=../../data/chroma

# Optional Meta WhatsApp Cloud API delivery
WHATSAPP_PROVIDER=meta
WHATSAPP_VERIFY_TOKEN=<meta-webhook-verify-token>
WHATSAPP_ACCESS_TOKEN=<meta-system-user-access-token>
WHATSAPP_PHONE_NUMBER_ID=<meta-phone-number-id>
WHATSAPP_API_VERSION=v20.0
```

WhatsApp bridge app:

```env
# apps/whatsapp/.env
BACKEND_URL=http://127.0.0.1:8000
BOT_NAME=SATARK
SURVEY_ID=
DEFAULT_LANGUAGE=en
REQUEST_TIMEOUT_MS=30000
BAILEYS_AUTH_DIR=auth_info_deployed
```

## Local Run

Backend:

```powershell
cd apps/api
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

Frontend:

```powershell
cd apps/web
npm install
npm run dev -- --host 127.0.0.1 --port 3001
```

WhatsApp bridge:

```powershell
cd apps/whatsapp
npm install
npm start
```

## Authentication

Use the SATARK login page role dropdown. Demo role passwords are shown on the login screen for local testing.

Important access:

- HSD / EnSD: Survey Design
- FOD: Field Operation and Data Collection
- C&QCD: Data Collection & Quality Assurance
- DIID / ASPD / CICD / CDD: National Intelligence & Statistical Output

## Channel API

All channels use the same backend scoring pipeline. Channel adapters only normalize input and output.

Start a session:

```http
POST /api/v1/channels/session/start
Authorization: Bearer <satark-token>
Content-Type: application/json

{
  "survey_id": "DDI-IND-MOSPI-PLFS26",
  "channel": "whatsapp",
  "respondent_ref": "+919900000000",
  "household_id": "HH-TN-0042",
  "enumerator_id": "enum_1",
  "language": "en"
}
```

Submit an answer:

```http
POST /api/v1/channels/answer
Authorization: Bearer <satark-token>
Content-Type: application/json

{
  "channel": "whatsapp",
  "respondent_ref": "+919900000000",
  "raw_answer": "Yes",
  "meta": {
    "elapsed_seconds": 14
  }
}
```

Fetch current question:

```http
GET /api/v1/channels/next?channel=whatsapp&respondent_ref=%2B919900000000
Authorization: Bearer <satark-token>
```

WhatsApp webhook:

```http
POST /api/v1/channels/whatsapp/webhook
Content-Type: application/json

{
  "sender": "+919900000000",
  "message": {
    "text": "Yes"
  },
  "survey_id": "DDI-IND-MOSPI-PLFS26"
}
```

IVR webhook:

```http
POST /api/v1/channels/ivr/webhook
Content-Type: application/json

{
  "CallSid": "CALL-123",
  "From": "+919900000000",
  "Digits": "1"
}
```

Avatar / voice transcript:

```http
POST /api/v1/channels/avatar/answer
Authorization: Bearer <satark-token>
Content-Type: application/json

{
  "respondent_ref": "avatar-001",
  "transcript": "I worked five days",
  "meta": {
    "elapsed_seconds": 21
  }
}
```

## Enumerator Client

Open:

```text
Login as FOD -> Field Operation -> Enumerator Client
```

The tab contains:

- App/Web CAPI collection client
- WhatsApp / IVR / AI-avatar / Web channel sandbox
- Live validation confidence
- Adaptive next-question output
- Paradata capture
- Response persistence refresh hook

## Google Translate

Set `VITE_GOOGLE_TRANSLATE_API_KEY` in `apps/web/.env.local`.

SATARK calls Google Translate from the frontend translation wrapper for:

- question labels
- option labels
- real-time language switching in the survey builder
- generated survey translation output

If Google rejects a language code or the key is unavailable, SATARK keeps the English source text and marks the translation as needing official review.

## Final National CSV

Open:

```text
Login as DIID / ASPD / CICD / CDD -> National Intelligence & Statistical Output Hub -> Cleansed Data Exports
```

Click **Generate Cleansed Export File**.

The downloaded CSV contains:

```csv
Response_ID,Survey_ID,Survey_Name,State,District,Pincode,Enumerator_ID,Interview_Date,Start_Time,End_Time,Duration_Minutes,Latitude,Longitude,GPS_Accuracy,Device_ID,Language,Trust_Score,Validation_Status,Structural_Check,Logic_Check,Statistical_Check,Semantic_Check,Historical_Check,Flag_Count,Flag_Type,Quality_Status,NIC_Code,NCO_Code,Export_Status,Created_At
```

Rows are built from current survey responses, paradata timings, GPS, trust score, validation layers, flags, coded answers, and LGD/pincode location data.

## Final QA Flow

1. Login as `hsd` or `ensd`.
2. Create a survey in **Survey Design**.
3. Publish it.
4. Login as `fod`.
5. Open **Field Operation** and deploy the survey to households/enumerators.
6. Open **Enumerator Client**.
7. Collect responses through the app client or the WhatsApp / IVR / avatar sandbox.
8. Confirm live validation and paradata are visible.
9. Open **Field Monitor** and confirm assignments/flags update.
10. Login as a data governance role.
11. Open **National Intelligence & Statistical Output Hub**.
12. Download the final complete CSV report.
