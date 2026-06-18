# SATARK 2.0 — Survey Designer (HSD + EnSD)

I would completely remove **SDRD** from the UI and rename it to:

```text
Survey Designer
(HSD + EnSD)
```

Because that aligns better with current MoSPI terminology.

---

# Final Left Navigation

```text
Survey Designer (HSD / EnSD)

├── My Surveys

├── Survey Builder

├── Database

├── Validation Center
```

---

# 1. MY SURVEYS

Purpose:

```text
Manage Surveys

Track Versions

Clone

Archive

Monitor Status
```

---

### Table

```text
Survey ID

Survey Name

Domain

Version

Created By

Status

Responses

Last Modified
```

---

Example

```text
DDI-IND-MOSPI-PLFS-2026

Youth Employment Survey

PLFS

v3.2

Published

24,220 Responses
```

---

# 2. SURVEY BUILDER

This remains your primary screen.

Keep:

```text
Goal

Language

Domain

Question Bank Upload

Generate
```

---

# IMPROVEMENT

After survey generation:

Add Toggle

```text
[ Flow Canvas ]

[ Design Canvas ]
```

---

# Flow Canvas

Purpose:

Survey Logic

Shows:

```text
Start

↓

Demographics

↓

Employment

↓

Income

↓

Migration

↓

End
```

Visual flowchart.

---

### Features

```text
Drag

Connect

Delete

Rearrange

Add Logic
```

---

### Used For

```text
Skip Logic

Conditional Logic

Loops

Survey Navigation
```

---

# Design Canvas

Purpose:

Question Editing

Shows:

```text
Section A

Question 1

Question 2

Question 3

Section B

Question 4
```

Like:

```text
Google Forms

Typeform
```

but government-oriented.

---

### Question Card

```text
Question

Response Type

Options

Validation

Code Mapping

Skip Logic

Language
```

---

### Example

```text
Did you work in the last 7 days?

Type:
Single Choice

Options:
Yes
No

Validation:
Mandatory
```

---

This is where officers spend 90% of their time.

---

# 3. DATABASE

This becomes the Knowledge Hub.

Split into:

```text
Question Bank Library

Code Library
```

---

# Question Bank Library

Contains:

```text
PLFS

HCES

ASUSE

Agriculture

Enterprise

Custom QBs
```

---

### Search

```text
Question

Topic

Survey

Domain
```

---

### Example

```text
Employment

Work Status

Migration

Income
```

---

# Code Library

Contains:

```text
NIC

NCO

ISCO

Industry Codes

Occupation Codes

MoSPI Standards
```

---

Example

```text
Tailoring Shop

↓

NIC 14101
```

---

# 4. VALIDATION CENTER

Purpose:

Quality Assurance

Survey Validation

Question Validation

---

### Layer 1

Structural

```text
Mandatory

Data Type

Range
```

---

### Layer 2

Question Design

```text
Complex Language

Jargon

Double Barrelled

Negative Wording
```

---

### Layer 3

Semantic Validation

LLM Assisted

Example:

```text
Question ambiguous

Question unclear

Question leading
```

---

### Layer 4

MoSPI Compliance

```text
DDI Metadata

Variable Naming

Coding Standards
```

---

# Improved SATARK RAG

Current RAG:

```text
Query

↓

Vector Search

↓

LLM

↓

Survey
```

Not enough.

---

# SATARK Survey Intelligence RAG

## Layer 1

Knowledge Sources

```text
Question Banks

MoSPI Surveys

Codebooks

Metadata

Classification Systems

Uploaded QB
```

---

## Layer 2

Structured Registry

Store:

```json
{
 "survey":"PLFS",
 "domain":"Labour",
 "section":"Employment",
 "question":"Did you work during the last 7 days?",
 "type":"single_choice",
 "validation":"mandatory"
}
```

---

## Layer 3

Hybrid Retrieval

```text
Metadata Search

+

BGE-M3 Search

+

BM25 Search
```

---

## Layer 4

Reranker

```text
BGE-Reranker-v2
```

---

## Layer 5

Context Builder

Build context using:

```text
User Goal

Domain

Retrieved Questions

Code Library

Survey Standards

Uploaded QB
```

---

## Layer 6

Survey Generator

Primary:

```text
Sarvam-M
```

Fallback:

``gemma4
```

---

## Layer 7

Question Validator

Every generated question passes:

```text
Language Simplicity Check

Jargon Check

Sensitivity Check

Skip Logic Check

Validation Check

Coding Check
```

---

# Additional Features To Win

## Question Quality Score

Every question:

```text
Clarity
95

Complexity
12%

Compliance
98%

Translation Quality
97%
```

---

## Duplicate Question Detection

Before generation:

```text
Question already exists in PLFS

Question reused from HCES

Question similar to NSS
```

---

## Question Recommendation

```text
Missing Income Section

Missing Migration Section

Missing Assets Section
```

AI suggests additions.

---

# 22 Language Support

Use:

```text
IndicTrans2
```

Primary

---

Fallback:

```text
Google Translate API
```

---

Supported:

```text
English
हिन्दी
தமிழ்
తెలుగు
ಕನ್ನಡ
മലയാളം
বাংলা
ગુજરાતી
ਪੰਜਾਬੀ
অসমীয়া
ଓଡ଼ିଆ
मराठी
اردو
संस्कृतम्
कोंकणी
डोगरी
मैथिली
नेपाली
बोडो
संथाली
कश्मीरी
मणिपुरी
```

---

# Final Survey Designer Architecture

```text
Survey Designer (HSD / EnSD)

├── My Surveys

├── Survey Builder
│     ├── Flow Canvas
│     └── Design Canvas

├── Database
│     ├── Question Bank Library
│     └── Code Library

├── Validation Center

└── Translation Center
```

---

# Final RAG Architecture

```text
Question Banks
+
PLFS
+
HCES
+
ASUSE
+
Agriculture
+
Enterprise
+
Code Library

↓

Structured Registry

↓

BGE-M3 Embeddings

↓

Qdrant

↓

Hybrid Retrieval

(Vector + BM25)

↓

BGE Reranker

↓

Context Builder

↓

Sarvam-M

↓

Question Generator

↓

Validation Engine

↓

Translation Engine

↓

Flow Canvas

↓

Design Canvas

↓

Publish
```

This is the version I would confidently show to MoSPI because it is simple, government-friendly, production-oriented, and focused on survey quality rather than AI complexity.
