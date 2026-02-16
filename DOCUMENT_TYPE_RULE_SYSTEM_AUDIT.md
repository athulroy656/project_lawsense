# READ-ONLY CODEBASE AUDIT: Document Type Detection & Rule System

**Date**: 2026-02-15
**Scope**: Document type detection, rule engines, type-aware behavior
**Status**: READ-ONLY AUDIT (No modifications made)

---

## A) DOCUMENT TYPE DETECTION

### Detection Location
**File**: `documents/document_type_detector.py`
**Function**: `detect_document_type(text: str) -> tuple[str, float, dict]` (Line 100)

### Detection Method
- **Approach**: Weighted pattern matching with regex
- **Input**: Extracted document text
- **Output**: `(detected_type, confidence_score, details)`

### Exact Labels Produced
The system recognizes **7 document types** (defined in `DOCUMENT_TYPE_RULES`, lines 7-97):

1. `NDA_MUTUAL` - "NDA (Mutual)"
2. `NDA_ONEWAY` - "NDA (One-way)"
3. `SERVICE_AGREEMENT` - "Service Agreement"
4. `PRIVACY_POLICY` - "Privacy Policy"
5. `TERMS_CONDITIONS` - "Terms & Conditions"
6. `EMPLOYMENT_AGREEMENT` - "Employment Agreement"
7. `OTHER` - "Other/Unknown" (fallback)

### Storage & Flow

**Database Storage** (`documents/models.py`, lines 25-30):
```python
document_type = models.CharField(
    max_length=30,
    choices=DOCUMENT_TYPES,
    default="OTHER"
)
detected_type_confidence = models.FloatField(default=0.0)
```

**When Stored** (`documents/views.py`, lines 141-154):
- Called during document upload/processing
- Only auto-detects if user didn't manually select type
- Saves to `document.document_type` and `document.detected_type_confidence`

**How Returned to Frontend** (`documents/serializers.py`, lines 6, 17, 24-25):
```python
document_type_display = serializers.SerializerMethodField()

def get_document_type_display(self, obj):
    return obj.get_document_type_display()
```
- Returns human-readable name (e.g., "NDA (Mutual)" instead of "NDA_MUTUAL")
- Included in document list/detail API responses

---

## B) RULE SYSTEM INVENTORY

### 1. Financial Extraction Rules

**File**: `documents/financial_utils.py`
**What it evaluates**: Monetary amounts, expiration dates, penalties, liability caps, deadlines, duration
**Rules defined**: Lines 1-456 (regex patterns, no document-type awareness)

**Key Functions**:
- `extract_expiration_info()` - Line 155
- `extract_penalties()` - Line 217
- `extract_liability_caps()` - Line 263
- `extract_deadlines()` - Line 332
- `extract_duration()` - Line 385
- `extract_all_financial_data()` - Line 437 (aggregator)

**Evidence of type-awareness**: **NONE**
```python
# Line 217: extract_penalties accepts doc_type but NEVER USES IT
def extract_penalties(document_text, doc_type="OTHER", purpose="Unknown"):
    # ... no conditional logic based on doc_type
```

### 2. Risk/Exposure Rules

**File**: `documents/risk_utils.py`
**What it evaluates**: Missing clauses, safety scores, risk flags, verdicts

**Rules defined**:
- `EXPECTED_CLAUSES` dict (Lines 201-260) - **TYPE-AWARE**
- `calculate_safety_score()` (Lines 17-61) - Type-agnostic
- `risk_flags()` (Lines 276-357) - Type-agnostic
- `risk_summary()` (Lines 360-407) - **Uses document type**

**Call chain**:
```
build_document_report() [Line 454]
  └─> risk_summary(document) [Line 490]
       └─> doc_type = document.document_type [Line 363]
       └─> expected_labels = EXPECTED_CLAUSES.get(doc_type, ...) [Line 377]
```

### 3. Loophole Rules

**File**: `documents/loophole_detector.py`
**What it evaluates**: Vague language, unlimited liability, weak IP rights, missing clauses

**Rules defined**:
- `LOOPHOLE_PATTERNS` dict (Lines 5-80) - **TYPE-AGNOSTIC** (global patterns)
- `GLOBAL_MISSING_CHECKS` dict (Lines 85-101) - Applied to all documents
- `TYPE_SPECIFIC_MISSING_CHECKS` dict (Lines 103-205) - **TYPE-AWARE**

**Evidence of type-awareness** (`_check_missing_clauses()`, lines 245-295):
```python
# Line 255-257
doc_type = getattr(document, "document_type", "OTHER")
if doc_type in TYPE_SPECIFIC_MISSING_CHECKS:
    checks_to_run.update(TYPE_SPECIFIC_MISSING_CHECKS[doc_type])
```

**Type-specific checks exist for**:
- `NDA_MUTUAL` (Lines 104-118)
- `NDA_ONEWAY` (Lines 127-141)
- `EMPLOYMENT_AGREEMENT` (Lines 143-164)
- `SERVICE_AGREEMENT` (Lines 166-187)
- `PRIVACY_POLICY` (Lines 189-204)

### 4. Clause Classification Rules

**File**: `documents/clause_rules.py`
**What it evaluates**: Clause label detection via regex patterns

**Rules defined**: `CLAUSE_RULES` dict (Lines 3-392)
- Contains ~50+ clause types with regex patterns
- **TYPE-AGNOSTIC** - Same patterns applied to all documents

**Evidence**:
```python
# Lines 3-100: Common clauses (all document types)
CLAUSE_RULES = {
    "Termination": [...],
    "Payment": [...],
    "Confidentiality": [...],
    # ... no conditional logic based on document type
}
```

---

## C) TYPE-AWARE RULES CHECK

### Answer: **PARTIALLY YES**

The system has **mixed behavior**:
- Some rule engines are type-aware
- Others apply globally regardless of document type

### Evidence of Type-Aware Rules

#### 1. Expected Clauses (RISK SCORING)
**File**: `documents/risk_utils.py`, Lines 201-260

```python
EXPECTED_CLAUSES = {
    "TERMS_CONDITIONS": [
        "Termination", "Payment", "Liability", "User Obligations", ...
    ],
    "NDA_MUTUAL": [
        "Definition of Confidential Information",
        "Exclusions from Confidential Information",
        ...
    ],
    "SERVICE_AGREEMENT": [
        "Termination", "Payment", "Force Majeure", ...
    ],
    # ... different lists for each type
}
```

**Usage** (Line 377):
```python
expected_labels = EXPECTED_CLAUSES.get(doc_type, EXPECTED_CLAUSES["OTHER"])
```

#### 2. Important Clauses Display (REPORT GENERATION)
**File**: `documents/risk_utils.py`, Lines 493-573

```python
# Line 494-509: TERMS_CONDITIONS
if doc_type == "TERMS_CONDITIONS":
    important_labels = [
        "User Obligations", "Liability", "Indemnification", ...
    ]
# Line 510-535: NDA_MUTUAL / NDA_ONEWAY
elif doc_type in ["NDA_MUTUAL", "NDA_ONEWAY"]:
    important_labels = [
        "Definition of Confidential Information", ...
    ]
# Line 536-546: SERVICE_AGREEMENT
elif doc_type == "SERVICE_AGREEMENT":
    important_labels = [
        "Payment", "Termination", "Liability", ...
    ]
# ... etc.
```

#### 3. Loophole Missing Clause Checks
**File**: `documents/loophole_detector.py`, Lines 103-205

```python
TYPE_SPECIFIC_MISSING_CHECKS = {
    "NDA_MUTUAL": {
        "permitted_disclosure": {...},
        "return_destruction": {...},
        "exclusions": {...}
    },
    "EMPLOYMENT_AGREEMENT": {
        "ip_assignment": {...},
        "termination_notice": {...},
        ...
    },
    # ... different checks per type
}
```

### Evidence of Type-Agnostic Rules

#### 1. Clause Classification Patterns
**File**: `documents/clause_rules.py`
- **NO** conditional logic based on document type
- Same regex patterns applied to all documents

#### 2. Financial Extraction
**File**: `documents/financial_utils.py`
- **NO** type-specific extraction logic
- `extract_penalties()` accepts `doc_type` parameter but **NEVER USES IT** (Line 217)

#### 3. Loophole Pattern Detection
**File**: `documents/loophole_detector.py`, Lines 5-80
- `LOOPHOLE_PATTERNS` dict is **GLOBAL**
- Applied to all documents regardless of type

#### 4. Safety Score Calculation
**File**: `documents/risk_utils.py`, Lines 17-61
- **NO** type-specific weighting
- Same penalty values for all document types

---

## D) CURRENT DOCUMENT TYPES (SUPPORTED TODAY)

### Complete List (7 types)

| Type Code | Human Label | Used By |
|-----------|-------------|---------|
| `NDA_MUTUAL` | "NDA (Mutual)" | Risk scoring, Important clauses, Loophole checks |
| `NDA_ONEWAY` | "NDA (One-way)" | Risk scoring, Important clauses, Loophole checks |
| `SERVICE_AGREEMENT` | "Service Agreement" | Risk scoring, Important clauses, Loophole checks |
| `PRIVACY_POLICY` | "Privacy Policy" | Risk scoring, Important clauses, Loophole checks |
| `TERMS_CONDITIONS` | "Terms & Conditions" | Risk scoring, Important clauses |
| `EMPLOYMENT_AGREEMENT` | "Employment Agreement" | Risk scoring, Important clauses, Loophole checks |
| `OTHER` | "Other/Unknown" | Fallback for all engines |

### Rule Engine Usage Matrix

| Engine | Type-Aware? | Which Types Used? |
|--------|-------------|-------------------|
| **Financial Extraction** | ❌ NO | None (global rules) |
| **Clause Classification** | ❌ NO | None (global patterns) |
| **Risk Scoring (Expected Clauses)** | ✅ YES | All 7 types |
| **Important Clauses Display** | ✅ YES | All 7 types |
| **Loophole Pattern Detection** | ❌ NO | None (global patterns) |
| **Loophole Missing Checks** | ✅ YES | NDA_MUTUAL, NDA_ONEWAY, EMPLOYMENT_AGREEMENT, SERVICE_AGREEMENT, PRIVACY_POLICY |
| **Safety Score Calculation** | ❌ NO | None (global weights) |

---

## E) OBSERVED GAPS (FACTUAL FINDINGS)

### 1. **Inconsistent Type Awareness Across Engines**
- **Finding**: Risk scoring uses document type, but financial extraction does not
- **Evidence**: `risk_utils.py` line 377 uses `doc_type`, but `financial_utils.py` has no type-conditional logic
- **Impact**: Financial data extraction may miss type-specific patterns (e.g., NDA-specific penalty clauses)

### 2. **Unused Parameter in Financial Extraction**
- **Finding**: `extract_penalties()` accepts `doc_type` parameter but never uses it
- **Evidence**: `financial_utils.py` line 217 signature includes `doc_type="OTHER"`, but function body has no conditional logic
- **Impact**: Dead code; misleading API signature

### 3. **Global Clause Classification Patterns**
- **Finding**: All documents use identical clause detection patterns regardless of type
- **Evidence**: `clause_rules.py` lines 3-392 - no `if doc_type ==` logic
- **Impact**: May misclassify clauses in specialized documents (e.g., NDA-specific clauses detected as generic "Confidentiality")

### 4. **Type-Specific Loophole Checks Missing for Some Types**
- **Finding**: `TERMS_CONDITIONS` and `OTHER` have no type-specific loophole checks
- **Evidence**: `loophole_detector.py` lines 103-205 - only 5 types have specific checks (NDA_MUTUAL, NDA_ONEWAY, EMPLOYMENT_AGREEMENT, SERVICE_AGREEMENT, PRIVACY_POLICY)
- **Impact**: Terms & Conditions documents only get global checks, may miss T&C-specific issues

### 5. **No Type-Specific Safety Score Weighting**
- **Finding**: All document types use identical penalty weights for risk scoring
- **Evidence**: `risk_utils.py` lines 17-61 - hardcoded values (0.8, 0.5, 0.25) with no `doc_type` branching
- **Impact**: Missing "Termination" clause penalized equally in NDA vs. Privacy Policy (different severity in practice)

### 6. **Document Type Confidence Not Used in Analysis**
- **Finding**: `detected_type_confidence` stored in DB but never consulted during analysis
- **Evidence**: `models.py` line 30 defines field; no grep results for usage in `risk_utils.py`, `loophole_detector.py`, or `financial_utils.py`
- **Impact**: Low-confidence type detection (e.g., 0.3) treated same as high-confidence (0.9)

### 7. **Manual Override Bypasses Cache But Not Logged**
- **Finding**: When user provides `document_type_override`, report cache is bypassed but no audit trail
- **Evidence**: `risk_utils.py` lines 469-491 - override bypasses cache, but no logging of override event
- **Impact**: Cannot track when/why manual overrides were used

### 8. **Expected Clauses List Inconsistency**
- **Finding**: NDA types have 10 core clauses, but SERVICE_AGREEMENT has 13, TERMS_CONDITIONS has 22
- **Evidence**: `risk_utils.py` lines 211-222 (NDA: 10 items), lines 202-209 (T&C: 22 items)
- **Impact**: Disproportionate "missing clause" penalties for different document types

### 9. **Purpose Detection Not Used in Type-Specific Logic**
- **Finding**: Legal-BERT detects document purpose, but purpose is not mapped to document type
- **Evidence**: `risk_utils.py` line 370 detects purpose; line 363 uses `document.document_type` (separate values)
- **Impact**: Purpose="Employment / Service engagement" may not align with `document_type="OTHER"`

### 10. **Frontend Hides Document Type But Backend Still Uses It**
- **Finding**: Recent frontend changes hide `document_type_display` from UI, but backend still relies on it for analysis
- **Evidence**: `Dashboard.jsx` lines 366-368, 938-942, 1358 (hidden with comments); `risk_utils.py` line 377 (still uses type)
- **Impact**: Users cannot see what type is being used for their analysis (transparency issue)

---

## SUMMARY

### System Architecture
- **Detection**: Regex-based pattern matching with confidence scoring
- **Storage**: Database field `document_type` (CharField with 7 choices)
- **Usage**: Mixed - some engines type-aware, others global

### Type-Aware Components
✅ Risk scoring (expected clauses)
✅ Important clauses display
✅ Type-specific loophole checks (5 of 7 types)

### Type-Agnostic Components
❌ Financial extraction
❌ Clause classification patterns
❌ Loophole pattern detection (global)
❌ Safety score weighting

### Key Observation
The system has **separate rule profiles** for expected clauses and important clause display, but **one global rule set** for clause detection, financial extraction, and loophole patterns. This creates inconsistent behavior where document type matters for some analyses but not others.

---

**END OF AUDIT**
