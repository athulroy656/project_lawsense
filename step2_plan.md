# Step 2 Implementation Plan: Context-Aware Loophole Detection

## Objective
Enhance the loophole detection system to be **context-aware**, identifying specific missing clauses based on the document type (NDA, Employment, SaaS, etc.) rather than just generic checks.

## Changes

### 1. `documents/loophole_detector.py`
- **Refactor `MISSING_CLAUSE_CHECKS`**: Split into `GLOBAL_MISSING_CHECKS` and `TYPE_SPECIFIC_MISSING_CHECKS`.
- **Update `_check_missing_clauses`**: 
    - Accept `doc_type` as an argument (or derive from `document.document_type`).
    - Merge global checks with type-specific checks.
- **Add Definitions**:
    - **NDA**: Check for "Permitted Disclosure", "Return of Info", "Exclusions".
    - **Employment**: Check for "Non-Compete", "IP Assignment".
    - **SaaS**: Check for "SLA", "Data Security".
    - **Privacy**: Check for "Cookie Policy", "User Rights".

### 2. `documents/risk_utils.py`
- Ensure `detect_loopholes` is called with necessary context if API changes (though `document` object has `document_type`, so signature change might not be strictly necessary if we use the object property).
- Verification of integration.

### 3. Verification
- Create `documents/step2_loophole_test.py` to mock documents of different types and verify correct missing clause detection.
