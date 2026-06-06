# SATARK.AI Phase 2 - Survey Intelligence Engine Roadmap

**From MVP to Production-Grade National Survey Platform**

---

## 🎯 Vision

Transform SATARK.AI from a deterministic survey generator into a **no-code, adaptive, persona-aware survey platform** aligned with MoSPI standards for NSS, PLFS, and NFHS surveys at national scale.

---

## 📊 Current State (Phase 1 - COMPLETED ✅)

### What We Have
- ✅ **Deterministic Survey Generation**: Rule-based + ML hybrid
- ✅ **Intent Parser**: spaCy + NLP rules
- ✅ **Domain Classifier**: TF-IDF + Logistic Regression
- ✅ **Question Retrieval**: SentenceTransformers + FAISS
- ✅ **Survey Builder**: Deterministic rule engine
- ✅ **Validation Engine**: Statistical checks
- ✅ **Question Bank**: 22 official questions
- ✅ **Multilingual**: English + Hindi support
- ✅ **Performance**: 0.26s average, 93.8% validation

### Architecture
```
FastAPI Backend + React Frontend
Single-server deployment
JSON-based question bank
In-memory embeddings (FAISS)
Basic validation rules
```

---

## 🚀 Target State (Phase 2 - PRODUCTION)

### New Capabilities Required

#### 1. **Immutable Core + Dynamic Layers**
- **Immutable Core**: NSS/PLFS standard blocks unchanged
- **Dynamic Layers**: Persona-based adaptive routing
- **Branching Logic**: Age/occupation-based question flow

#### 2. **Data Prefill via Aadhaar e-KYC**
- UIDAI API integration
- Masked demographics
- Privacy-first tokenization
- Session-based security (JWT/AES-256)

#### 3. **Triangulated Validation**
- **Layer 1**: JSON Schema + constraints (range/logic)
- **Layer 2**: Anomaly detection (IsolationForest)
- **Layer 3**: Consistency checks (Phi-3-mini LLM)
- **Cross-validation**: Citizen + enumerator + external data

#### 4. **Paradata Analytics**
- Enumerator behavior tracking
- Time/GPS clustering
- Error heatmaps
- Risk scoring (K-means + Isolation Forest)

#### 5. **Multimodal Collection**
- Web (React)
- Mobile (Flutter, offline-first)
- WhatsApp (Twilio integration)
- IVR (AI4Bharat voice)
- Face authentication (FaceNet)

#### 6. **Enhanced Multilingual**
- 22 Indic languages + English
- IndicTrans2 (AI4Bharat)
- Dynamic translation
- Language d