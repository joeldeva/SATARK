# SATARK.AI - Survey Response Interface Guide

## Overview

SATARK.AI now has **two interfaces**:

1. **Survey Designer Interface** - For creating surveys (http://localhost:3000)
2. **Survey Respondent Interface** - For filling out surveys (http://localhost:3000/respond)

---

## 🎨 Survey Designer Interface

**URL:** http://localhost:3000

**Purpose:** For survey designers, administrators, and researchers to create surveys

**Features:**
- ✅ Natural language survey generation
- ✅ AI-powered question selection
- ✅ Domain classification
- ✅ Real-time validation
- ✅ GSBPM compliance checking
- ✅ Survey editing and customization
- ✅ Export capabilities

**How to Use:**
1. Open http://localhost:3000
2. Enter a survey description (e.g., "Survey for farmers about crop production")
3. Select languages and max questions
4. Click "Generate Survey"
5. Review and edit the generated survey
6. Export or deploy

---

## 📝 Survey Respondent Interface

**URL:** http://localhost:3000/respond

**Purpose:** For survey respondents (citizens, enumerators) to fill out surveys

**Features:**
- ✅ Step-by-step question navigation
- ✅ Progress tracking
- ✅ Input validation
- ✅ Required field checking
- ✅ Multiple question types support:
  - Single choice (radio buttons)
  - Multiple choice (checkboxes)
  - Number input (with range validation)
  - Text input (short and long)
- ✅ Previous/Next navigation
- ✅ Response summary
- ✅ Submission confirmation

**How to Use:**
1. Open http://localhost:3000/respond
2. Read the instructions
3. Answer questions one by one
4. Use "Previous" and "Next" buttons to navigate
5. Required questions are marked with *
6. Click "Submit Survey" when done
7. Receive confirmation

---

## 🔄 Switching Between Interfaces

### From Designer to Respondent:
- Click the "📝 Fill Survey" button in the top-right corner
- Or navigate to http://localhost:3000/respond

### From Respondent to Designer:
- Click the "🎨 Design Survey" button in the top-right corner
- Or navigate to http://localhost:3000

---

## 📊 Question Types Supported

### 1. Single Choice (Radio Buttons)
- Example: "What is your gender?"
- Options: Male, Female, Other
- User can select only one option

### 2. Multiple Choice (Checkboxes)
- Example: "Do you own any livestock?"
- Options: Cattle, Goat/Sheep, Poultry, Other, None
- User can select multiple options

### 3. Number Input
- Example: "What is your age?"
- Validation: Min/max range checking
- Example: Age must be between 0-120

### 4. Text Input
- Example: "What is your occupation?"
- Short text or long text (multiline)
- Optional pattern validation

---

## ✅ Validation Features

### Real-time Validation:
- ✅ Required field checking
- ✅ Number range validation
- ✅ Format validation
- ✅ Error messages displayed immediately

### Before Submission:
- ✅ All required questions must be answered
- ✅ All responses must pass validation
- ✅ Summary shows completion percentage

---

## 🎯 User Experience Features

### Progress Tracking:
- Visual progress bar at the top
- "Question X of Y" indicator
- Percentage completion shown
- Response summary at bottom

### Navigation:
- "Previous" button to go back
- "Next" button to continue
- "Submit Survey" on last question
- Stepper shows all questions (desktop only)

### Visual Feedback:
- Current question highlighted
- Answered questions marked
- Error messages in red
- Success confirmation on submission

---

## 📱 Responsive Design

The interface works on:
- ✅ Desktop computers
- ✅ Tablets
- ✅ Mobile phones (responsive layout)
- ✅ Different screen sizes

---

## 🔒 Security & Privacy

### Data Protection:
- ✅ Responses encrypted in transit
- ✅ No data stored in browser (except during session)
- ✅ Secure submission to backend
- ✅ DPDP Act compliant

### Privacy Features:
- ✅ Anonymous responses (optional)
- ✅ No tracking cookies
- ✅ Data used for statistical purposes only
- ✅ Government-grade security

---

## 🚀 Current Status

### ✅ Implemented:
- Survey designer interface
- Survey respondent interface
- Question navigation
- Input validation
- Progress tracking
- Submission handling
- Responsive design

### 🔄 Coming Soon (Phase 2):
- Offline support (mobile app)
- Multi-language switching
- Save and resume later
- Photo/audio responses
- GPS location capture
- Biometric authentication
- WhatsApp integration
- IVR (voice) surveys

---

## 🧪 Testing the Response Interface

### Test Survey 1: Agriculture
1. Go to http://localhost:3000/respond
2. Survey loads automatically (farmers survey)
3. Answer 10 questions about farming
4. Submit and see confirmation

### Test Survey 2: Custom Survey
1. Go to http://localhost:3000 (designer)
2. Generate a custom survey
3. Click "📝 Fill Survey" button
4. Fill out your custom survey
5. Submit

---

## 📊 Response Data Format

When a survey is submitted, the data looks like:

```json
{
  "survey_id": "5c141c71-1917-4fcc-9682-8836a409765b",
  "responses": [
    {
      "question_id": "Q001",
      "response_value": "28"
    },
    {
      "question_id": "Q002",
      "response_value": "1"
    }
  ],
  "metadata": {
    "completed_at": "2026-02-09T12:00:00Z",
    "time_taken": 180,
    "device": "web"
  }
}
```

---

## 🛠️ For Developers

### File Structure:
```
frontend/src/
├── App.jsx                      # Survey designer interface
├── RespondentApp.jsx            # Survey respondent interface
├── index.js                     # Router (switches between apps)
└── components/
    ├── PromptInput.jsx          # Survey generation input
    ├── SurveyCanvas.jsx         # Survey preview/editor
    ├── ValidationPanel.jsx      # Validation display
    └── SurveyResponseForm.jsx   # Survey filling form (NEW)
```

### Adding New Question Types:
Edit `SurveyResponseForm.jsx` and add a new case in `renderQuestionInput()`:

```javascript
case 'your_new_type':
  return (
    <YourCustomInput
      value={response}
      onChange={(value) => handleResponseChange(question.id, value)}
    />
  );
```

### Customizing Validation:
Edit `validateCurrentQuestion()` in `SurveyResponseForm.jsx`

---

## 📞 Support

- **Documentation:** This file
- **API Docs:** http://localhost:8000/docs
- **Backend Status:** http://localhost:8000/health
- **Frontend:** http://localhost:3000

---

## 🎉 Quick Start

1. **Backend is running:** http://localhost:8000 ✅
2. **Frontend is running:** http://localhost:3000 ✅

**To fill a survey:**
- Open http://localhost:3000/respond
- Answer questions
- Submit

**To design a survey:**
- Open http://localhost:3000
- Enter prompt
- Generate survey

---

**Status:** ✅ Both interfaces are fully operational and ready to use!
