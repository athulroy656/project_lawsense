# QUICK START: Document Summariser

## ✅ BACKEND COMPLETE

All backend code is implemented and ready to use:

1. ✅ Model fields added (`summary_text`, `summary_generated_at`)
2. ✅ Summariser function added (`generate_plain_language_summary`)
3. ✅ API endpoint created (`POST /api/summarize/`)
4. ✅ URL route configured

---

## 🔧 MIGRATION NEEDED

Run this when server is restarted:

```bash
py manage.py makemigrations documents --name add_summary_fields
py manage.py migrate documents
```

---

## 🧪 TEST THE ENDPOINT

Once migration is run, test with:

```bash
curl -X POST http://localhost:8000/api/summarize/ \
  -H "Content-Type: application/json" \
  -d "{\"document_id\": 1}"
```

Expected response:
```json
{
  "summary_text": "1) Purpose\n...",
  "generated_at": "2026-02-15T15:10:00Z",
  "used_cache": false,
  "document_id": 1
}
```

Second call should return `"used_cache": true`

---

## 📱 FRONTEND INTEGRATION

See `DOCUMENT_SUMMARISER_IMPLEMENTATION.md` for complete frontend code examples.

### Quick Summary:

1. **Add state**:
```javascript
const [summary, setSummary] = useState(null);
const [summaryLoading, setSummaryLoading] = useState(false);
```

2. **Add button**:
```jsx
<button onClick={() => handleSummarize(docId)}>
    📄 Summarize (Plain Language)
</button>
```

3. **Call API**:
```javascript
const response = await fetch('/api/summarize/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ document_id: docId })
});
const data = await response.json();
setSummary(data);
```

4. **Display summary** in a separate section from analysis

---

## 🎯 KEY FEATURES

- ✅ **Isolated**: Separate from analysis pipeline
- ✅ **Cached**: Subsequent calls use cached summary
- ✅ **Descriptive**: No legal advice or risk judgments
- ✅ **Safe**: Says "Not found" instead of hallucinating
- ✅ **Graceful**: Handles Ollama not running

---

## 📊 EXAMPLE OUTPUT

```
1) Purpose
This document is a Terms of Service agreement for a web application.

2) Parties / Roles
- Service Provider: The company offering the service
- User: The person or entity using the service

3) Key obligations
• Users must be 18 years or older to use the service
• Users agree not to misuse the platform or violate laws
• Service provider can terminate accounts for violations
• Users retain ownership of their content
• Service provider has license to use content for operations

4) Money & dates
• Subscription: $9.99/month or $99/year
• Free trial: 14 days
• Billing cycle: Monthly on signup date
• Cancellation: Anytime, no refunds for partial months

5) Key sections
• Acceptable use policy (no spam, harassment, illegal content)
• Intellectual property rights and licensing
• Limitation of liability (capped at subscription fees)
• Dispute resolution through binding arbitration
• Automatic renewal unless cancelled
```

---

## ⚠️ IMPORTANT

- Does NOT break existing features
- Does NOT auto-generate on upload
- Only generates when user clicks button
- Requires Ollama to be running

---

**Next Step**: Run migration, then test endpoint!
