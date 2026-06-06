# SATARK.AI - User Guide

**Quick Start Guide for Survey Officers**

---

## 🎯 What is SATARK.AI?

SATARK.AI is an intelligent survey generation system that creates government-compliant surveys from simple text descriptions. Just describe what you need, and the system generates a complete, validated survey ready for deployment.

### Key Benefits
- ⚡ **Fast**: Generate surveys in seconds
- 🎯 **Accurate**: Uses official government questions
- 🔒 **Secure**: Works completely offline
- ✅ **Compliant**: Follows MoSPI and GSBPM standards
- 🌐 **Multilingual**: Supports 13 Indian languages

---

## 🚀 Getting Started

### Step 1: Access the System

**Web Interface**: Open http://localhost:3000 in your browser  
**API Documentation**: Visit http://localhost:8000/docs

### Step 2: Describe Your Survey

In the prompt box, describe your survey needs in plain English. Be specific about:
- **Target audience**: Who will take the survey?
- **Topic**: What is the survey about?
- **Domain**: Labour, Health, Agriculture, etc.
- **Special requirements**: Income questions, satisfaction ratings, etc.

### Step 3: Generate

Click "Generate Survey" and wait 1-2 seconds. The system will:
1. Analyze your prompt
2. Classify the domain
3. Retrieve relevant official questions
4. Build a structured survey
5. Validate the quality

### Step 4: Review & Edit

Review the generated survey:
- Check question relevance
- Verify question order
- Edit text if needed
- Add or remove questions

### Step 5: Export & Deploy

Export your survey in the desired format:
- JSON (for APIs)
- PDF (for printing)
- Excel (for analysis)
- ODK (for mobile data collection)

---

## 📝 Example Prompts

### Good Prompts (Specific & Clear)

#### Example 1: Labour Survey
```
Survey for urban youth aged 18-30 about employment status, 
job satisfaction, and income levels
```
**Result**: 10 questions covering employment, occupation, work hours, satisfaction, income

#### Example 2: Health Survey
```
Survey for rural women about healthcare access, insurance 
coverage, and maternal health services
```
**Result**: 8 questions covering facility visits, insurance, satisfaction, expenses

#### Example 3: Agriculture Survey
```
Survey for farmers about crop production, land ownership, 
and agricultural income
```
**Result**: 10 questions covering land, crops, farming income, occupation

#### Example 4: Enterprise Survey
```
Survey for small business owners about enterprise type, 
number of employees, and annual revenue
```
**Result**: 10 questions covering business operations, employees, revenue

#### Example 5: Household Survey
```
Comprehensive household survey for income assessment 
and asset ownership
```
**Result**: 12 questions covering household size, income, assets, occupation

### Poor Prompts (Too Vague)

❌ "Make a survey"  
❌ "Survey about people"  
❌ "Questions"  

**Why?** These don't specify domain, audience, or topic.

---

## 🎨 Understanding the Interface

### Main Components

#### 1. Prompt Input Panel (Top)
- **Text Box**: Enter your survey description
- **Language Selector**: Choose survey languages (EN, HI, etc.)
- **Max Questions**: Set the number of questions (3-50)
- **Domain Selector**: Optionally force a specific domain
- **Generate Button**: Start survey generation

#### 2. Survey Canvas (Center)
- **Survey Title**: Auto-generated from your prompt
- **Question List**: All questions in order
- **Question Editor**: Click any question to edit
- **Add/Remove**: Buttons to modify questions
- **Reorder**: Drag to change question order

#### 3. Validation Panel (Right)
- **Validation Score**: Overall quality score (0-100%)
- **Errors**: Critical issues that must be fixed
- **Warnings**: Suggestions for improvement
- **Standards Check**: GSBPM/MoSPI compliance

#### 4. Engine Trace (Bottom)
- **Processing Steps**: What the system did
- **Timing**: How long each step took
- **Method**: Which engine was used
- **Audit Trail**: Complete generation history

---

## 🔍 Understanding Survey Domains

SATARK.AI supports 7 main domains:

### 1. Labour
**Topics**: Employment, occupation, work hours, income, job satisfaction  
**Use For**: Employment surveys, workforce studies, labour force surveys  
**Example Questions**: Employment status, occupation type, work hours, salary

### 2. Health
**Topics**: Healthcare access, insurance, facility visits, medical expenses  
**Use For**: Health surveys, maternal health, disease surveillance  
**Example Questions**: Facility visits, insurance coverage, satisfaction, expenses

### 3. Agriculture
**Topics**: Land ownership, crops, farming income, agricultural practices  
**Use For**: Agricultural surveys, crop production, farmer welfare  
**Example Questions**: Land ownership, main crops, farming income

### 4. Enterprise
**Topics**: Business type, employees, revenue, operations  
**Use For**: Business surveys, MSME studies, industrial surveys  
**Example Questions**: Enterprise type, employee count, annual turnover

### 5. Education
**Topics**: Educational attainment, barriers, access  
**Use For**: Education surveys, literacy studies, school enrollment  
**Example Questions**: Education level, barriers to education

### 6. Household
**Topics**: Household size, income, assets, consumption  
**Use For**: Household surveys, consumption studies, welfare assessment  
**Example Questions**: Household size, total income, asset ownership

### 7. Demographic
**Topics**: Age, gender, location, basic demographics  
**Use For**: All surveys (automatically included)  
**Example Questions**: Age, gender, location type, education

---

## ⚙️ Advanced Features

### Multi-Language Support

SATARK.AI supports 13 Indian languages:
- English (en)
- Hindi (hi)
- Bengali (bn)
- Telugu (te)
- Tamil (ta)
- Marathi (mr)
- Gujarati (gu)
- Kannada (kn)
- Malayalam (ml)
- Odia (or)
- Punjabi (pa)
- Assamese (as)
- Urdu (ur)

**How to Use**:
1. Select languages in the language dropdown
2. System automatically includes translations
3. Questions appear in all selected languages

### Question Types

SATARK.AI supports 8 question types:

1. **Single Choice**: Select one option (radio buttons)
2. **Multiple Choice**: Select multiple options (checkboxes)
3. **Number**: Numeric input with validation
4. **Text**: Free text response
5. **Date**: Date picker
6. **Scale**: Rating scale (1-5, 1-10, etc.)
7. **Matrix**: Grid of questions
8. **Boolean**: Yes/No questions

### Validation Rules

Automatic validation includes:
- **Range Checks**: Min/max values for numbers
- **Required Fields**: Mandatory questions
- **Pattern Matching**: Format validation (phone, email, etc.)
- **Cross-Field Checks**: Logical consistency between questions
- **Skip Logic**: Conditional question display

### Routing & Skip Logic

Questions can have routing rules:
- **Show If**: Display question only if condition is met
- **Skip To**: Jump to specific question based on answer
- **Condition**: Complex logical expressions

**Example**:
```
Q1: Are you employed? (Yes/No)
Q2: What is your occupation? (Show if Q1 = Yes)
Q3: What is your income? (Show if Q1 = Yes)
```

---

## 📊 Quality Indicators

### Validation Score

The validation score (0-100%) indicates survey quality:

- **90-100%**: Excellent - Ready for deployment
- **80-89%**: Good - Minor improvements suggested
- **70-79%**: Fair - Some issues to address
- **Below 70%**: Poor - Significant improvements needed

### What Affects the Score?

✅ **Positive Factors**:
- Appropriate number of questions (8-20)
- Mix of question types
- Proper demographic coverage
- Official source questions
- Valid routing logic
- Complete translations

❌ **Negative Factors**:
- Too few questions (< 3)
- Too many questions (> 50)
- Missing demographics
- Duplicate questions
- Invalid routing
- Missing translations

---

## 🛠️ Troubleshooting

### Issue: "No questions generated"
**Cause**: Prompt too vague or domain not recognized  
**Solution**: Be more specific about domain and topic

### Issue: "Same questions for different surveys"
**Cause**: Limited question bank for that domain  
**Solution**: System will improve as question bank expands

### Issue: "Validation score too low"
**Cause**: Survey structure issues  
**Solution**: Check validation panel for specific errors

### Issue: "Questions not relevant"
**Cause**: Domain misclassification  
**Solution**: Manually select domain in dropdown

### Issue: "Missing translations"
**Cause**: Language not fully supported yet  
**Solution**: English translations always available

---

## 💡 Best Practices

### 1. Write Clear Prompts
- Specify target audience
- Mention key topics
- Include special requirements
- Use domain keywords

### 2. Review Generated Surveys
- Check question relevance
- Verify question order
- Test skip logic
- Validate translations

### 3. Keep Surveys Focused
- 8-15 questions is optimal
- One main topic per survey
- Avoid mixing unrelated domains
- Include only necessary demographics

### 4. Test Before Deployment
- Preview with sample data
- Test on mobile devices
- Verify skip logic works
- Check all translations

### 5. Use Official Questions
- SATARK.AI uses government-approved questions
- Don't modify official question text
- Maintain standard codes (NCO, NIC, etc.)
- Follow MoSPI guidelines

---

## 📞 Support & Resources

### Documentation
- **Architecture**: See `SATARK_ARCHITECTURE.md`
- **System Status**: See `SYSTEM_STATUS.md`
- **API Docs**: http://localhost:8000/docs

### Quick Commands

**Check System Health**:
```bash
curl http://localhost:8000/health
```

**Generate Survey via API**:
```bash
curl -X POST http://localhost:8000/generate-survey \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Your survey description", "languages": ["en"], "max_questions": 10}'
```

**View System Info**:
```bash
curl http://localhost:8000/system-info
```

---

## 🎓 Training Resources

### For Survey Officers
1. Understanding survey domains
2. Writing effective prompts
3. Reviewing and editing surveys
4. Quality validation
5. Export and deployment

### For Administrators
1. System architecture
2. Question bank management
3. Adding new domains
4. Performance monitoring
5. Compliance verification

---

## ✅ Checklist: Creating Your First Survey

- [ ] Open SATARK.AI web interface
- [ ] Write a clear, specific prompt
- [ ] Select target languages
- [ ] Set appropriate question count
- [ ] Click "Generate Survey"
- [ ] Review generated questions
- [ ] Check validation score
- [ ] Edit if necessary
- [ ] Verify translations
- [ ] Export in desired format
- [ ] Test before deployment

---

**Last Updated**: February 6, 2026  
**Version**: 1.0.0  
**Status**: Production Ready
