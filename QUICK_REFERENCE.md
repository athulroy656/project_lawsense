# Quick Reference: Code Changes

## 1. Q&A Document Isolation

### Backend API Change
**Before:**
```python
# documents/views.py
def ask_question(request):
    question = request.data.get('question')
    answer = qa_answer(question)
    return Response({"question": question, "answer": answer})
```

**After:**
```python
# documents/views.py
def ask_question(request):
    question = request.data.get('question')
    document_id = request.data.get('document_id')  # REQUIRED
    
    if not document_id:
        return Response({"error": "document_id is required"}, status=400)
    
    doc = get_doc_or_404_safe(document_id, request.user)
    user_id = request.user.id if request.user.is_authenticated else None
    
    answer = qa_answer(question, document_id=document_id, user_id=user_id)
    return Response({"question": question, "answer": answer, "document_id": document_id})
```

### Frontend API Call Change
**Before:**
```javascript
// frontend/src/api.js
export async function askQuestion(question) {
  const res = await fetch(`${API_BASE}/ask/`, {
    method: "POST",
    headers: getHeaders(),
    body: JSON.stringify({ question }),
  });
  return handleResponse(res);
}
```

**After:**
```javascript
// frontend/src/api.js
export async function askQuestion(question, documentId) {
  const res = await fetch(`${API_BASE}/ask/`, {
    method: "POST",
    headers: getHeaders(),
    body: JSON.stringify({ question, document_id: documentId }),
  });
  return handleResponse(res);
}
```

### Frontend Usage Change
**Before:**
```javascript
// frontend/src/pages/Dashboard.jsx
const submitQuestion = async () => {
    if (!question.trim()) return;
    const res = await askQuestion(question);
    setAnswer(res.answer);
};
```

**After:**
```javascript
// frontend/src/pages/Dashboard.jsx
const submitQuestion = async () => {
    if (!question.trim()) return;
    
    if (!selectedDoc) {
        showToast("Please select a document first", "error");
        return;
    }
    
    const res = await askQuestion(question, selectedDoc.id);
    setAnswer(res.answer);
};
```

---

## 2. Report Caching

### Usage (Transparent)
```python
# documents/views.py
def document_report(request, document_id):
    doc = get_doc_or_404_safe(document_id, request.user)
    
    # This now uses caching automatically
    report = build_document_report(doc)
    
    return Response(report)
```

### Cache Invalidation
```python
# When you update analysis logic, increment version:
# documents/risk_utils.py
RULES_VERSION = "v1.3.0"  # Changed from v1.2.0
```

### Manual Cache Clear (if needed)
```python
# In Django shell or management command
from documents.models import Document

# Clear all caches
Document.objects.update(report_cache=None, report_cached_at=None, report_cache_key=None)

# Clear specific document cache
doc = Document.objects.get(id=123)
doc.report_cache = None
doc.report_cached_at = None
doc.report_cache_key = None
doc.save()
```

---

## 3. Loophole Detector Fix

### Before (Dead Code)
```python
# documents/loophole_detector.py
if not has_relevant_clauses:
    # Comment explaining the issue
    pass  # This does nothing!
```

### After (Working Code)
```python
# documents/loophole_detector.py
if not has_relevant_clauses:
    # Concept text exists but wasn't classified as expected label
    # Override has_concept to flag as missing
    has_concept = False
```

---

## 4. Vector Store Metadata

### Before
```python
# documents/vector_utils.py
metadatas.append({
    "document_id": document.id,
    "label": clause.label,
    "clause_id": clause.id,
})
```

### After
```python
# documents/vector_utils.py
metadata = {
    "document_id": document.id,
    "label": clause.label,
    "clause_id": clause.id,
}
# Add user_id for user-scoped filtering
if document.user_id:
    metadata["user_id"] = document.user_id
metadatas.append(metadata)
```

---

## Testing Commands

```bash
# Run all tests
pytest documents/tests_*.py -v

# Run specific test suites
pytest documents/tests_qa_isolation.py -v
pytest documents/tests_report_caching.py -v
pytest documents/tests_loophole_refinement.py -v

# Run with coverage
pytest documents/tests_*.py --cov=documents --cov-report=html

# Run migration
python manage.py migrate documents
```

---

## Deployment Checklist

- [ ] Review all code changes
- [ ] Run test suite (all tests pass)
- [ ] Run database migration
- [ ] Test Q&A with multiple documents
- [ ] Verify report caching works
- [ ] Check loophole detection accuracy
- [ ] Monitor for any errors in production
- [ ] Update API documentation (document_id now required for Q&A)
