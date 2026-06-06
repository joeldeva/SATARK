# Phase 2 Implementation Plan - Survey Intelligence Engine

## Immediate Priorities (Next 2 Weeks)

### Priority 1: Expand Question Bank (100+ Questions)
**Timeline:** 3-4 days  
**Impact:** HIGH - Core functionality improvement

#### Tasks:
1. **Download MoSPI Official Questions**
   - NSS 78th Round (Employment & Unemployment)
   - PLFS Annual Report 2022-23
   - NFHS-5 Questionnaires
   - ASI Schedule

2. **Structure Questions by Domain**
   ```
   Labour: 30 questions (employment, wages, hours, occupation)
   Health: 25 questions (access, insurance, maternal, child health)
   Agriculture: 20 questions (land, crops, livestock, income)
   Education: 15 questions (enrollment, barriers, expenditure)
   Household: 20 questions (composition, income, assets, consumption)
   Enterprise: 15 questions (type, employees, revenue, challenges)
   Social: 10 questions (caste, religion, migration)
   Demographic: 10 questions (age, gender, marital status, location)
   ```

3. **Add NCO/NIC/ISIC Mappings**
   - Occupation codes (NCO-2015)
   - Industry codes (NIC-2008)
   - International codes (ISIC Rev.4)

#### Files to Update:
- `satark_backend/database/question_bank.json` (expand to 100+ questions)
- `satark_backend/database/coding_standards.json` (add NCO/NIC/ISIC)
- `satark_backend/database/routing_rules.json` (complex skip logic)

---

### Priority 2: Enhanced Validation Engine (Layer 3)
**Timeline:** 2-3 days  
**Impact:** HIGH - Quality assurance

#### Implementation:

**File:** `satark_backend/ml/coherence_validator.py`

```python
"""
Layer 3 Validation: LLM-based Coherence Check
Uses Phi-3-mini (3.8B) for open-text response validation
"""

from transformers import AutoModelForCausalLM, AutoTokenizer
import torch
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class CoherenceValidator:
    """
    Lightweight LLM validation for open-text responses.
    Advisory flags only - does not reject responses.
    """
    
    def __init__(self):
        """Initialize Phi-3-mini model."""
        self.model_name = "microsoft/Phi-3-mini-4k-instruct"
        self.model = None
        self.tokenizer = None
        self._load_model()
    
    def _load_model(self):
        """Load Phi-3-mini model (3.8B parameters)."""
        try:
            logger.info("Loading Phi-3-mini for coherence validation...")
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_name,
                trust_remote_code=True
            )
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                torch_dtype=torch.float16,
                device_map="auto",
                trust_remote_code=True
            )
            logger.info("✅ Phi-3-mini loaded successfully")
        except Exception as e:
            logger.warning(f"⚠️ Could not load Phi-3-mini: {e}")
            self.model = None
    
    def validate_response(
        self,
        question: str,
        answer: str,
        context: Optional[Dict] = None
    ) -> Dict:
        """
        Check if answer is coherent with question.
        Returns advisory flags, not rejections.
        """
        if not self.model or not answer or len(answer.strip()) < 5:
            return {
                "coherent": True,
                "confidence": 1.0,
                "flags": [],
                "method": "skip"
            }
        
        try:
            # Create validation prompt
            prompt = self._create_validation_prompt(question, answer, context)
            
            # Generate validation
            inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=100,
                temperature=0.1,
                do_sample=False
            )
            
            response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            # Parse response
            result = self._parse_validation_response(response)
            
            return result
            
        except Exception as e:
            logger.error(f"Coherence validation error: {e}")
            return {
                "coherent": True,
                "confidence": 0.5,
                "flags": ["validation_error"],
                "method": "error"
            }
    
    def _create_validation_prompt(
        self,
        question: str,
        answer: str,
        context: Optional[Dict]
    ) -> str:
        """Create prompt for coherence check."""
        prompt = f"""You are validating survey responses for statistical quality.

Question: {question}
Answer: {answer}

Is this answer coherent and reasonable for the question?
Consider:
1. Does the answer address the question?
2. Is the answer logically consistent?
3. Are there obvious errors or contradictions?

Respond with: COHERENT or FLAG: [reason]
"""
        return prompt
    
    def _parse_validation_response(self, response: str) -> Dict:
        """Parse LLM validation response."""
        response_lower = response.lower()
        
        if "coherent" in response_lower and "flag" not in response_lower:
            return {
                "coherent": True,
                "confidence": 0.9,
                "flags": [],
                "method": "llm"
            }
        else:
            # Extract flag reason
            flags = []
            if "flag:" in response_lower:
                reason = response.split("FLAG:")[-1].strip()[:100]
                flags.append(reason)
            
            return {
                "coherent": False,
                "confidence": 0.7,
                "flags": flags,
                "method": "llm"
            }
    
    def batch_validate(
        self,
        responses: List[Dict]
    ) -> List[Dict]:
        """Validate multiple responses efficiently."""
        results = []
        
        for resp in responses:
            result = self.validate_response(
                question=resp.get("question", ""),
                answer=resp.get("answer", ""),
                context=resp.get("context")
            )
            results.append(result)
        
        return results
```

**Integration:** Update `satark_backend/core/validation_engine.py` to include Layer 3

---

### Priority 3: Paradata Tracking System
**Timeline:** 2-3 days  
**Impact:** HIGH - Enumerator quality control

#### Implementation:

**File:** `satark_backend/analytics/paradata_analyzer.py`

```python
"""
Paradata Analytics Engine
Tracks enumerator behavior, response times, GPS patterns
"""

import numpy as np
from sklearn.cluster import KMeans
from sklearn.ensemble import IsolationForest
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class ParadataAnalyzer:
    """
    Analyze survey paradata for quality control.
    Inspired by susoparaviewer methodology.
    """
    
    def __init__(self):
        """Initialize paradata analyzer."""
        self.enumerator_profiles = {}
        self.anomaly_detector = IsolationForest(contamination=0.1)
        self.clusterer = KMeans(n_clusters=3)  # Low/Medium/High risk
    
    def track_response(
        self,
        survey_id: str,
        question_id: str,
        enumerator_id: str,
        response_data: Dict
    ) -> Dict:
        """
        Track individual response with paradata.
        
        Captures:
        - Time taken to answer
        - GPS coordinates (if available)
        - Device info
        - Edit history
        - Timestamp
        """
        paradata = {
            "survey_id": survey_id,
            "question_id": question_id,
            "enumerator_id": enumerator_id,
            "timestamp": datetime.now().isoformat(),
            "time_taken_seconds": response_data.get("time_taken", 0),
            "gps_lat": response_data.get("gps_lat"),
            "gps_lon": response_data.get("gps_lon"),
            "device_id": response_data.get("device_id"),
            "edit_count": response_data.get("edit_count", 0),
            "response_length": len(str(response_data.get("answer", ""))),
            "method": response_data.get("method", "manual")  # manual/voice/prefill
        }
        
        # Update enumerator profile
        self._update_enumerator_profile(enumerator_id, paradata)
        
        return paradata
    
    def _update_enumerator_profile(
        self,
        enumerator_id: str,
        paradata: Dict
    ):
        """Update enumerator behavior profile."""
        if enumerator_id not in self.enumerator_profiles:
            self.enumerator_profiles[enumerator_id] = {
                "total_responses": 0,
                "avg_time_per_question": 0,
                "total_edits": 0,
                "gps_locations": [],
                "response_times": [],
                "last_active": None
            }
        
        profile = self.enumerator_profiles[enumerator_id]
        profile["total_responses"] += 1
        profile["total_edits"] += paradata.get("edit_count", 0)
        profile["response_times"].append(paradata["time_taken_seconds"])
        profile["last_active"] = paradata["timestamp"]
        
        if paradata.get("gps_lat") and paradata.get("gps_lon"):
            profile["gps_locations"].append({
                "lat": paradata["gps_lat"],
                "lon": paradata["gps_lon"],
                "timestamp": paradata["timestamp"]
            })
        
        # Update average
        profile["avg_time_per_question"] = np.mean(profile["response_times"])
    
    def detect_anomalies(
        self,
        enumerator_id: str
    ) -> Dict:
        """
        Detect anomalous behavior patterns.
        
        Checks:
        - Too fast responses (speeding)
        - Too slow responses (distraction)
        - Suspicious GPS patterns
        - High edit rates
        - Unusual response patterns
        """
        if enumerator_id not in self.enumerator_profiles:
            return {"anomalies": [], "risk_score": 0}
        
        profile = self.enumerator_profiles[enumerator_id]
        anomalies = []
        risk_score = 0
        
        # Check response time anomalies
        times = profile["response_times"]
        if len(times) > 10:
            avg_time = np.mean(times)
            std_time = np.std(times)
            
            # Too fast (speeding)
            if avg_time < 5:  # Less than 5 seconds average
                anomalies.append("speeding")
                risk_score += 30
            
            # High variance (inconsistent)
            if std_time > avg_time * 2:
                anomalies.append("inconsistent_timing")
                risk_score += 20
        
        # Check edit rate
        edit_rate = profile["total_edits"] / max(profile["total_responses"], 1)
        if edit_rate > 0.5:  # More than 50% edited
            anomalies.append("high_edit_rate")
            risk_score += 25
        
        # Check GPS patterns
        gps_locs = profile["gps_locations"]
        if len(gps_locs) > 5:
            # Check if all responses from same location (suspicious)
            lats = [loc["lat"] for loc in gps_locs]
            lons = [loc["lon"] for loc in gps_locs]
            
            if np.std(lats) < 0.001 and np.std(lons) < 0.001:
                anomalies.append("static_location")
                risk_score += 35
        
        return {
            "enumerator_id": enumerator_id,
            "anomalies": anomalies,
            "risk_score": min(risk_score, 100),
            "risk_level": self._get_risk_level(risk_score)
        }
    
    def _get_risk_level(self, score: int) -> str:
        """Categorize risk level."""
        if score < 30:
            return "low"
        elif score < 60:
            return "medium"
        else:
            return "high"
    
    def generate_heatmap_data(
        self,
        region: Optional[str] = None
    ) -> Dict:
        """
        Generate error heatmap data for admin dashboard.
        Groups errors by geography and enumerator.
        """
        heatmap_data = {
            "by_enumerator": {},
            "by_location": {},
            "by_time": {}
        }
        
        for enum_id, profile in self.enumerator_profiles.items():
            anomaly_result = self.detect_anomalies(enum_id)
            
            heatmap_data["by_enumerator"][enum_id] = {
                "risk_score": anomaly_result["risk_score"],
                "risk_level": anomaly_result["risk_level"],
                "total_responses": profile["total_responses"],
                "avg_time": profile["avg_time_per_question"]
            }
        
        return heatmap_data
    
    def get_enumerator_metrics(
        self,
        enumerator_id: str
    ) -> Dict:
        """Get detailed metrics for specific enumerator."""
        if enumerator_id not in self.enumerator_profiles:
            return {"error": "Enumerator not found"}
        
        profile = self.enumerator_profiles[enumerator_id]
        anomalies = self.detect_anomalies(enumerator_id)
        
        return {
            "enumerator_id": enumerator_id,
            "total_responses": profile["total_responses"],
            "avg_time_per_question": profile["avg_time_per_question"],
            "total_edits": profile["total_edits"],
            "edit_rate": profile["total_edits"] / max(profile["total_responses"], 1),
            "unique_locations": len(profile["gps_locations"]),
            "last_active": profile["last_active"],
            "risk_score": anomalies["risk_score"],
            "risk_level": anomalies["risk_level"],
            "anomalies": anomalies["anomalies"]
        }
```

---

### Priority 4: Admin Dashboard MVP
**Timeline:** 3-4 days  
**Impact:** HIGH - Operational visibility

#### Components to Create:

1. **Dashboard Overview** (`frontend/src/pages/AdminDashboard.jsx`)
2. **Error Heatmap** (`frontend/src/components/ErrorHeatmap.jsx`)
3. **Enumerator Metrics** (`frontend/src/components/EnumeratorMetrics.jsx`)
4. **Real-time Stats** (`frontend/src/components/RealTimeStats.jsx`)

#### Features:
- Survey completion rates
- Response quality scores
- Enumerator performance rankings
- Geographic error distribution
- Time-series analytics
- Export functionality

---

## Implementation Schedule

### Week 1 (Days 1-7)
- **Day 1-2:** Expand question bank to 50 questions
- **Day 3-4:** Implement Layer 3 validation (Phi-3-mini)
- **Day 5-6:** Build paradata tracking system
- **Day 7:** Testing and integration

### Week 2 (Days 8-14)
- **Day 8-9:** Expand question bank to 100+ questions
- **Day 10-11:** Create admin dashboard MVP
- **Day 12-13:** Add NCO/NIC/ISIC coding
- **Day 14:** End-to-end testing with synthetic data

---

## Success Criteria

### Question Bank
- ✅ 100+ official MoSPI-style questions
- ✅ All 8 domains covered
- ✅ NCO/NIC/ISIC mappings complete
- ✅ Complex routing logic implemented

### Validation
- ✅ Layer 3 coherence check operational
- ✅ <1% false positive rate
- ✅ Advisory flags working
- ✅ Integration with existing layers

### Paradata
- ✅ Real-time tracking functional
- ✅ Anomaly detection accurate
- ✅ Risk scoring calibrated
- ✅ Heatmap generation working

### Dashboard
- ✅ Real-time metrics display
- ✅ Enumerator rankings visible
- ✅ Error patterns identifiable
- ✅ Export functionality working

---

## Next Steps After Phase 2

1. **Aadhaar e-KYC Integration** (Week 3)
2. **IndicTrans2 Multilingual** (Week 4)
3. **WhatsApp/IVR Channels** (Week 5)
4. **Flutter Mobile App** (Week 6)
5. **Production Deployment** (Week 7-8)

---

**Document Version:** 1.0  
**Created:** February 6, 2026  
**Owner:** SATARK.AI Development Team
