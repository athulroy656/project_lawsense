# SEMANTIC FALLBACK IMPLEMENTATION GUIDE

## Overview
This document explains the minimal changes needed to add semantic fallback to clause detection.

---

## IMPLEMENTATION STATUS

### ✅ COMPLETED
1. Created `documents/clause_validator.py` - LLM validation module
2. Added `retrieve_similar_clauses()` to `documents/legal_bert_engine.py`
3. Added `detection_method` field to `Clause` model

### ⏳ PENDING
1. Database migration (run after server restart)
2. Integration into `process_document()` workflow
3. Testing with sample documents

---

## STEP-BY-STEP INTEGRATION

### Step 1: Run Database Migration

```bash
# After restarting server (to avoid import errors)
py manage.py makemigrations documents --name add_clause_detection_method
py manage.py migrate documents
```

This adds the `detection_method` field to track how each clause was detected.

---

### Step 2: Modify `documents/views.py` - Add Semantic Fallback

**Location**: In `process_document()` function, after regex-based clause detection

**Current Flow** (lines ~138-160):
```python
def process_document(doc):
    # ... existing code ...
    
    # Classify clauses using regex
    classified_clauses = classify_clauses(doc.extracted_text)
    
    # Store clauses
    store_clauses(doc)
```

**New Flow** (add after `classify_clauses` but before `store_clauses`):

```python
def process_document(doc):
    # ... existing code ...
    
    # Step 1: Classify clauses using regex (existing)
    classified_clauses = classify_clauses(doc.extracted_text)
    
    # Step 2: SEMANTIC FALLBACK - Check for missing key clauses
    semantic_clauses = perform_semantic_fallback(doc, classified_clauses)
    
    # Step 3: Merge results
    all_clauses = classified_clauses + semantic_clauses
    
    # Store clauses (existing)
    store_clauses_with_method(doc, all_clauses)
```

---

### Step 3: Add Helper Functions to `documents/views.py`

Add these functions near the `process_document()` function:

```python
def perform_semantic_fallback(document, regex_clauses):
    """
    Perform semantic fallback for key clauses not found by regex.
    
    Args:
        document: Document instance
        regex_clauses: List of clauses found by regex
        
    Returns:
        list: Additional clauses found via semantic validation
    """
    from .clause_validator import KEY_STRUCTURAL_CLAUSES, validate_clause_match, should_use_semantic_fallback
    from .legal_bert_engine import LegalBertEngine
    import logging
    
    logger = logging.getLogger(__name__)
    semantic_clauses = []
    
    # Get labels already found by regex
    found_labels = {clause['label'] for clause in regex_clauses}
    
    # Check which key clauses are missing
    missing_key_clauses = [
        label for label in KEY_STRUCTURAL_CLAUSES.keys()
        if label not in found_labels and should_use_semantic_fallback(label)
    ]
    
    if not missing_key_clauses:
        logger.info(f"Document {document.id}: All key clauses found by regex")
        return []
    
    logger.info(f"Document {document.id}: Attempting semantic fallback for {len(missing_key_clauses)} clauses")
    
    try:
        bert_engine = LegalBertEngine.get_instance()
        
        for clause_label in missing_key_clauses:
            clause_description = KEY_STRUCTURAL_CLAUSES[clause_label]
            
            # Retrieve semantically similar paragraphs
            similar_paragraphs = bert_engine.retrieve_similar_clauses(
                document, 
                clause_description, 
                top_k=3
            )
            
            if not similar_paragraphs:
                continue
            
            # Validate the top match with LLM
            top_match = similar_paragraphs[0]
            validation_result = validate_clause_match(clause_label, top_match['text'])
            
            # Add clause based on validation status
            if validation_result['status'] == 'VALID_MATCH':
                semantic_clauses.append({
                    'label': clause_label,
                    'text': top_match['text'],
                    'detection_method': 'SEMANTIC',
                    'confidence': validation_result['confidence'],
                    'evidence': validation_result['evidence']
                })
                logger.info(f"Document {document.id}: Found '{clause_label}' via semantic validation (confidence: {validation_result['confidence']})")
                
            elif validation_result['status'] == 'POSSIBLE_MATCH':
                semantic_clauses.append({
                    'label': clause_label,
                    'text': top_match['text'],
                    'detection_method': 'POSSIBLE',
                    'confidence': validation_result['confidence'],
                    'evidence': validation_result['evidence']
                })
                logger.info(f"Document {document.id}: Possible match for '{clause_label}' (confidence: {validation_result['confidence']})")
    
    except Exception as e:
        logger.error(f"Semantic fallback error for document {document.id}: {e}")
    
    return semantic_clauses


def store_clauses_with_method(document, clauses_with_metadata):
    """
    Store clauses with detection method tracking.
    
    Args:
        document: Document instance
        clauses_with_metadata: List of dicts with {label, text, detection_method}
    """
    from .models import Clause
    
    # Clear existing clauses
    Clause.objects.filter(document=document).delete()
    
    # Create new clause objects
    clause_objects = []
    for clause_data in clauses_with_metadata:
        clause_objects.append(Clause(
            document=document,
            label=clause_data['label'],
            text=clause_data['text'],
            detection_method=clause_data.get('detection_method', 'REGEX')
        ))
    
    # Bulk create
    Clause.objects.bulk_create(clause_objects)
```

---

### Step 4: Update `classify_clauses()` to Return Metadata

**Location**: `documents/views.py` or wherever `classify_clauses()` is defined

**Current** (returns list of Clause objects):
```python
def classify_clauses(text):
    # ... regex logic ...
    return clauses  # List of Clause objects
```

**Updated** (returns list of dicts with metadata):
```python
def classify_clauses(text):
    # ... existing regex logic ...
    
    # Return as dicts instead of Clause objects
    clause_data = []
    for clause in clauses:
        clause_data.append({
            'label': clause.label,
            'text': clause.text,
            'detection_method': 'REGEX'  # Explicit marking
        })
    return clause_data
```

---

## BEHAVIOR FLOW DIAGRAM

```
┌─────────────────────────────────────┐
│ process_document(doc)               │
└─────────────────┬───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│ Step 1: Regex-based Detection       │
│ classify_clauses(text)              │
│ → Returns clauses with              │
│   detection_method='REGEX'          │
└─────────────────┬───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│ Step 2: Identify Missing Key        │
│ Clauses                             │
│ → Compare found vs KEY_STRUCTURAL   │
└─────────────────┬───────────────────┘
                  │
                  ▼
         ┌────────┴────────┐
         │ Missing clauses? │
         └────────┬────────┘
                  │
         ┌────────┴────────┐
         │                 │
        YES               NO
         │                 │
         ▼                 ▼
┌─────────────────┐  ┌──────────────┐
│ Step 3: Semantic│  │ Skip fallback│
│ Fallback        │  └──────┬───────┘
│                 │         │
│ For each missing│         │
│ clause:         │         │
│                 │         │
│ 3a. Retrieve    │         │
│     similar     │         │
│     paragraphs  │         │
│     (BERT +     │         │
│     ChromaDB)   │         │
│                 │         │
│ 3b. Validate    │         │
│     top match   │         │
│     (LLM)       │         │
│                 │         │
│ 3c. Parse JSON  │         │
│     result      │         │
└────────┬────────┘         │
         │                  │
         └────────┬─────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│ Step 4: Merge Results               │
│ all_clauses = regex + semantic      │
└─────────────────┬───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│ Step 5: Store Clauses               │
│ store_clauses_with_method()         │
│ → Saves with detection_method field │
└─────────────────────────────────────┘
```

---

## DETECTION METHOD LABELS

| Method | Meaning | Confidence |
|--------|---------|------------|
| `REGEX` | Found by regex pattern | High (explicit) |
| `SEMANTIC` | Validated by LLM as VALID_MATCH | Medium-High |
| `POSSIBLE` | Validated by LLM as POSSIBLE_MATCH | Medium-Low |

---

## KEY STRUCTURAL CLAUSES (10 Total)

These clauses trigger semantic fallback if not found by regex:

1. Limitation of Liability
2. Indemnification
3. Termination
4. Governing Law
5. Dispute Resolution
6. Arbitration
7. Confidentiality
8. Force Majeure
9. Severability
10. Entire Agreement

---

## PERFORMANCE CONSIDERATIONS

### When Semantic Fallback Triggers
- **ONLY** when regex fails to find a key structural clause
- **NOT** for every clause (keeps performance impact minimal)

### Typical Scenarios
- **Best case**: All key clauses found by regex → No fallback (0 LLM calls)
- **Common case**: 1-2 key clauses missing → 1-2 LLM calls
- **Worst case**: All 10 key clauses missing → 10 LLM calls

### Optimization
- Semantic retrieval is fast (BERT + ChromaDB vector search)
- LLM validation is the bottleneck (~1-2 seconds per clause)
- Total added time: ~2-20 seconds depending on missing clauses

---

## TESTING CHECKLIST

### Test Case 1: All Clauses Found by Regex
- **Input**: Well-structured NDA with explicit clause headers
- **Expected**: No semantic fallback triggered
- **Verify**: All clauses have `detection_method='REGEX'`

### Test Case 2: Missing Key Clause (Implicit Language)
- **Input**: Document with "Limitation of Liability" written as "Our maximum responsibility is limited to..."
- **Expected**: Semantic fallback finds it
- **Verify**: Clause has `detection_method='SEMANTIC'` and confidence > 0.7

### Test Case 3: Ambiguous Language
- **Input**: Paragraph vaguely related to termination but not explicit
- **Expected**: Marked as `POSSIBLE` or `NOT_A_MATCH`
- **Verify**: Either `detection_method='POSSIBLE'` or clause not stored

### Test Case 4: Completely Missing Clause
- **Input**: Document genuinely missing "Arbitration" clause
- **Expected**: LLM returns NOT_A_MATCH, clause not stored
- **Verify**: Clause does not appear in database

---

## EXPLAINABILITY

### For Users
- Regex matches: "Found explicitly in document"
- Semantic matches: "Found using AI validation (confidence: X%)"
- Possible matches: "Possibly present but ambiguous"

### For Developers
- Check `Clause.detection_method` field
- Review LLM validation evidence in logs
- Compare regex vs semantic detection rates

---

## ROLLBACK PLAN

If semantic fallback causes issues:

1. **Quick disable**: Comment out `perform_semantic_fallback()` call in `process_document()`
2. **Partial disable**: Reduce `KEY_STRUCTURAL_CLAUSES` to only critical clauses
3. **Full rollback**: Remove migration, revert model changes

---

## FILES MODIFIED SUMMARY

| File | Changes | Lines Added |
|------|---------|-------------|
| `documents/clause_validator.py` | **NEW** - LLM validation | ~150 |
| `documents/legal_bert_engine.py` | Added `retrieve_similar_clauses()` | ~50 |
| `documents/models.py` | Added `detection_method` field | ~10 |
| `documents/views.py` | Added semantic fallback logic | ~80 |
| **TOTAL** | | **~290 lines** |

---

## NEXT STEPS

1. ✅ Code written (clause_validator.py, legal_bert_engine.py, models.py)
2. ⏳ Run migration (after server restart)
3. ⏳ Integrate into views.py (add helper functions)
4. ⏳ Test with sample documents
5. ⏳ Monitor performance and accuracy

---

**Status**: Implementation 60% complete. Core modules ready, integration pending.
