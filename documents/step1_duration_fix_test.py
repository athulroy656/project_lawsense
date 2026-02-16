
import sys
import re
from unittest.mock import MagicMock

# Mock dependencies
sys.modules["documents.legal_bert_engine"] = MagicMock()
sys.modules["documents.nlp_utils"] = MagicMock()

# Simple mock for split_into_clauses
def simple_split(text):
    return [s.strip() for s in text.split('.') if s.strip()]

sys.modules["documents.nlp_utils"].split_into_clauses = simple_split

from documents.financial_utils import extract_duration

print("=== STEP 1 BUGFIX: DURATION FALSE POSITIVES ===\n")

tests = [
    {
        "name": "Positive: Standard 12 months", 
        "text": "The initial term of this Agreement is 12 months.", 
        "expect_found": True, 
        "expect_term": "12 months" 
    },
    {
        "name": "Positive: Remain in Force 2 years", 
        "text": "This Agreement shall remain in force for two (2) years.", 
        "expect_found": True, 
        "expect_term": "years" 
    },
    # UPDATED NEGATIVE: Contains "period" to trigger keyword check
    {
        "name": "Negative: NDA Return/Destroy (False Positive)", 
        "text": "Within a period of seven (7) days of written request, Receiving Party shall return or destroy Confidential Information.", 
        "expect_found": False
    },
    {
        "name": "Negative: Payment Due", 
        "text": "Payment is due within a period of 30 days of invoice.", 
        "expect_found": False
    },
    {
        "name": "Negative: Notice Period", 
        "text": "Either party may terminate the period with 30 days' notice.", 
        "expect_found": False
    },
    {
        "name": "Negative: No later than",
        "text": "Services must be completed no later than 5 days after commencement.",
        "expect_found": False
    }
]

failures = 0
for t in tests:
    res = extract_duration(t["text"])
    found = res["found"]
    term = res.get("term", "")
    
    status = "PASS"
    fail_msg = ""
    
    if t["expect_found"] and not found:
        status = "FAIL"
        fail_msg = "(Expected Found, got None)"
    elif not t["expect_found"] and found:
        status = "FAIL"
        # Only fail if it found a term
        fail_msg = f"(Expected NOT Found, got '{term}')"
    elif t["expect_found"] and t.get("expect_term") and t["expect_term"] not in str(term):
        status = "FAIL"
        fail_msg = f"(Expected term containing '{t['expect_term']}', got '{term}')"
        
    print(f"[{status}] {t['name']} {fail_msg}")
    if status == "FAIL": failures += 1

if failures == 0:
    print("\nALL TESTS PASSED")
else:
    print(f"\n{failures} TESTS FAILED")
