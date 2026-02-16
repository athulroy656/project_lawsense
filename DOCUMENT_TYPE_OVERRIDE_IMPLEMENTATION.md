# Document Type Override Implementation Summary

## Overview
Implemented minimal changes to hide auto-detected document type from UI and add manual override option in Advanced Settings.

---

## AUDIT RESULTS

### A) Document Type Storage & Usage

**Model**: `documents/models.py`
- `document_type` field (line 25-29): CharField with DOCUMENT_TYPES choices
- `detected_type_confidence` field (line 30): FloatField (0.0-1.0)

**Usage in Report Generation**: `documents/risk_utils.py`
- `build_document_report(document)` function (line 454)
- Uses `document.document_type` to determine important clauses (line 484)
- Document-type-specific logic for TERMS_CONDITIONS, NDA_MUTUAL, SERVICE_AGREEMENT, etc.

### B) Run Analysis Endpoint

**Endpoint**: `GET /api/documents/{id}/report/`
**File**: `documents/views.py` (line 222)
**Original Payload**: Query params: `?ai_summary=true` (optional)

### C) UI Display Locations (All Hidden)

**File**: `frontend/src/pages/Dashboard.jsx`
1. Line 364-372: Analysis Highlights section - **HIDDEN**
2. Line 923: Document header title fallback - **KEPT** (fallback only)
3. Line 938-942: Document metadata "Type" field - **HIDDEN**
4. Line 1358: Document Statistics section - **HIDDEN**

---

## IMPLEMENTATION

### PART 1: Frontend Changes

#### File: `frontend/src/pages/Dashboard.jsx`

**1. Added State Variables** (Lines 44-46)
```javascript
const [docTypeOverride, setDocTypeOverride] = useState("AUTO");
const [showAdvancedSettings, setShowAdvancedSettings] = useState(false);
```

**2. Updated API Calls** (Lines 131, 278)
```javascript
// When loading document
fetchDocumentReport(doc.id, false, docTypeOverride)

// When generating AI summary
fetchDocumentReport(selectedDoc.id, true, docTypeOverride)
```

**3. Hidden Auto-Detected Type** (Lines 366-368, 938-942, 1358)
- Removed from Analysis Highlights
- Removed from Document header metadata
- Removed from Document Statistics
- Added comments: `// Document Type - HIDDEN (auto-detection not shown)`

**4. Added Advanced Settings Section** (Lines 1218-1307)
```javascript
<div> {/* Advanced Settings Card */}
  <button onClick={() => setShowAdvancedSettings(!showAdvancedSettings)}>
    ⚙️ Advanced Settings
  </button>
  
  {showAdvancedSettings && (
    <div>
      <label>Document Type Override (Optional)</label>
      <select value={docTypeOverride} onChange={(e) => setDocTypeOverride(e.target.value)}>
        <option value="AUTO">Auto-detect (Default)</option>
        <option value="NDA_MUTUAL">NDA (Mutual)</option>
        <option value="NDA_ONEWAY">NDA (One-way)</option>
        <option value="SERVICE_AGREEMENT">Service Agreement</option>
        <option value="TERMS_CONDITIONS">Terms & Conditions</option>
        <option value="EMPLOYMENT_AGREEMENT">Employment Agreement</option>
        <option value="PRIVACY_POLICY">Privacy Policy</option>
        <option value="OTHER">Other/Unknown</option>
      </select>
      
      {docTypeOverride !== "AUTO" && (
        <div className="info-banner">
          ℹ️ Analysis will use {docTypeOverride} expectations.
        </div>
      )}
    </div>
  )}
</div>
```

#### File: `frontend/src/api.js`

**Updated fetchDocumentReport** (Lines 121-135)
```javascript
export async function fetchDocumentReport(documentId, includeAI = false, docTypeOverride = null) {
  let url = `${API_BASE}/documents/${documentId}/report/`;
  const params = new URLSearchParams();
  
  if (includeAI) params.append('ai_summary', 'true');
  if (docTypeOverride && docTypeOverride !== 'AUTO') {
    params.append('document_type_override', docTypeOverride);
  }
  
  const queryString = params.toString();
  if (queryString) url += `?${queryString}`;
  
  const res = await fetch(url, { headers: getHeaders() });
  return handleResponse(res);
}
```

---

### PART 2: Backend Changes

#### File: `documents/views.py`

**Updated document_report endpoint** (Lines 220-237)
```python
@api_view(['GET'])
@permission_classes([AllowAny])
def document_report(request, document_id):
    doc = get_doc_or_404_safe(document_id, request.user)

    # Check for manual document type override
    doc_type_override = request.query_params.get('document_type_override', None)
    
    # Validate override if provided
    valid_types = [choice[0] for choice in doc._meta.get_field('document_type').choices]
    if doc_type_override and doc_type_override not in valid_types:
        doc_type_override = None  # Ignore invalid override
    
    # Build report with optional override
    report = build_document_report(doc, document_type_override=doc_type_override)
    
    # ... rest of function
```

#### File: `documents/risk_utils.py`

**Updated build_document_report function** (Lines 454-491)
```python
def build_document_report(document, document_type_override=None):
    """
    Build a combined report for a document.
    
    CACHING: Reports are cached in the database to avoid recomputation.
    Cache is invalidated when:
    - Document text changes (tracked via uploaded_at)
    - RULES_VERSION changes
    - document_type_override is provided (bypasses cache)
    """
    import hashlib
    from django.utils import timezone
    
    # If override is provided, skip cache and use override type
    if document_type_override:
        # Bypass cache when override is used
        summary_data = risk_summary(document)
        doc_type = document_type_override
    else:
        # Generate cache key based on document state and rules version
        cache_key_data = f"{document.id}:{document.uploaded_at.isoformat()}:{RULES_VERSION}"
        cache_key = hashlib.sha256(cache_key_data.encode()).hexdigest()
        
        # Check if we have a valid cached report
        if (document.report_cache and 
            document.report_cache_key == cache_key and 
            document.report_cached_at):
            # Cache hit - return cached report
            return document.report_cache
        
        # Cache miss - compute report
        summary_data = risk_summary(document)
        doc_type = document.document_type
    
    # Document-type-specific important clauses
    if doc_type == "TERMS_CONDITIONS":
        # ... type-specific logic uses doc_type
```

**Skip caching when override is used** (Lines 698-707)
```python
# Only cache if no override was used
if not document_type_override:
    serializable_report = make_json_serializable(report)
    document.report_cache = serializable_report
    document.report_cached_at = timezone.now()
    document.report_cache_key = cache_key
    document.save(update_fields=['report_cache', 'report_cached_at', 'report_cache_key'])

return report
```

---

## MINIMAL DIFF SUMMARY

### Files Changed: 4

1. **frontend/src/pages/Dashboard.jsx** (~100 lines)
   - Added 2 state variables
   - Hidden 4 display locations
   - Added Advanced Settings section (~90 lines)
   - Updated 2 API calls

2. **frontend/src/api.js** (~15 lines)
   - Updated fetchDocumentReport to accept and send override

3. **documents/views.py** (~15 lines)
   - Added override parameter extraction and validation
   - Passed override to build_document_report

4. **documents/risk_utils.py** (~25 lines)
   - Added document_type_override parameter
   - Bypass cache when override is provided
   - Skip saving cache when override is used

**Total**: ~155 lines changed across 4 files

---

## EXAMPLE REQUEST PAYLOADS

### Without Override (Default Behavior)
```
GET /api/documents/123/report/
```

### With Override (Manual Type Selection)
```
GET /api/documents/123/report/?document_type_override=NDA_MUTUAL
```

### With Override + AI Summary
```
GET /api/documents/123/report/?ai_summary=true&document_type_override=SERVICE_AGREEMENT
```

---

## UI SCREENSHOT DESCRIPTION

**Location**: Dashboard page, after Deadlines card, before AI Summary section

**Collapsed State**:
```
┌─────────────────────────────────────────┐
│ ⚙️ ADVANCED SETTINGS              ▶    │
└─────────────────────────────────────────┘
```

**Expanded State**:
```
┌─────────────────────────────────────────┐
│ ⚙️ ADVANCED SETTINGS              ▼    │
├─────────────────────────────────────────┤
│ Document Type Override (Optional)       │
│ By default, the system auto-detects... │
│                                         │
│ ┌─────────────────────────────────────┐ │
│ │ Auto-detect (Default)          ▼   │ │
│ └─────────────────────────────────────┘ │
│                                         │
│ [When non-AUTO selected:]               │
│ ┌─────────────────────────────────────┐ │
│ │ ℹ️ Analysis will use NDA MUTUAL    │ │
│ │ expectations. Click "Generate AI    │ │
│ │ Summary" to re-analyze with this    │ │
│ │ type.                               │ │
│ └─────────────────────────────────────┘ │
└─────────────────────────────────────────┘
```

**Dropdown Options**:
- Auto-detect (Default)
- NDA (Mutual)
- NDA (One-way)
- Service Agreement
- Terms & Conditions
- Employment Agreement
- Privacy Policy
- Other/Unknown

---

## TESTING REQUIREMENTS

### Case 1: Auto Mode (Default)
**Steps**:
1. Upload document
2. Click "Analyze"
3. Leave Advanced Settings collapsed or set to "Auto-detect"

**Expected**:
- ✅ Report uses auto-detected type (same as before)
- ✅ Report is cached normally
- ✅ No document type shown in UI

### Case 2: Manual Override (NDA)
**Steps**:
1. Upload service agreement (auto-detected as SERVICE_AGREEMENT)
2. Expand Advanced Settings
3. Select "NDA (Mutual)"
4. Click "Generate AI Summary"

**Expected**:
- ✅ Report uses NDA expectations (missing clauses, risk scoring)
- ✅ Report is NOT cached (override bypasses cache)
- ✅ Info banner shows "Analysis will use NDA MUTUAL expectations"

### Case 3: Switch Back to Auto
**Steps**:
1. After Case 2, change dropdown back to "Auto-detect"
2. Click "Generate AI Summary"

**Expected**:
- ✅ Report reverts to auto-detected type
- ✅ Caching resumes normally
- ✅ Info banner disappears

---

## EVIDENCE MAP

### Files Changed

| File | Function/Section | Lines | Change Type |
|------|-----------------|-------|-------------|
| `frontend/src/pages/Dashboard.jsx` | State variables | 44-46 | Added |
| `frontend/src/pages/Dashboard.jsx` | Analysis Highlights | 366-368 | Hidden |
| `frontend/src/pages/Dashboard.jsx` | Document header | 938-942 | Hidden |
| `frontend/src/pages/Dashboard.jsx` | Document stats | 1358 | Hidden |
| `frontend/src/pages/Dashboard.jsx` | Advanced Settings | 1218-1307 | Added |
| `frontend/src/pages/Dashboard.jsx` | loadDocument call | 131 | Modified |
| `frontend/src/pages/Dashboard.jsx` | generateAISummary call | 278 | Modified |
| `frontend/src/api.js` | fetchDocumentReport | 121-135 | Modified |
| `documents/views.py` | document_report | 220-237 | Modified |
| `documents/risk_utils.py` | build_document_report | 454-491 | Modified |
| `documents/risk_utils.py` | Cache saving | 698-707 | Modified |

### Conditions Changed

**Before**:
```python
# Backend
report = build_document_report(doc)

# Frontend
fetchDocumentReport(doc.id)
```

**After**:
```python
# Backend
doc_type_override = request.query_params.get('document_type_override', None)
report = build_document_report(doc, document_type_override=doc_type_override)

# Frontend
fetchDocumentReport(doc.id, false, docTypeOverride)
```

---

## VALIDATION

✅ Auto-detection logic NOT deleted (kept internal)
✅ Document type NOT shown in normal UI
✅ Manual override dropdown in Advanced Settings
✅ Override passed to backend via query param
✅ Backend validates override against valid types
✅ Report uses override type for analysis
✅ Cache bypassed when override is used
✅ No changes to authentication, RAG, embeddings, risk scoring logic
✅ Minimal and localized changes
✅ No new dependencies

**Status**: ✅ **IMPLEMENTATION COMPLETE**
