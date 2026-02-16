
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

from documents.financial_utils import extract_duration, extract_all_financial_data

# Start Check
print("=== STEP 1: DURATION SAFETY & DEADLINES PRE-CHECK ===\n")

# We need to manually check for `extract_deadlines` first or mock it if not present
try:
    from documents.financial_utils import extract_deadlines
    print("extract_deadlines exists.")
except ImportError:
    print("extract_deadlines does NOT exist (Expected).")

# Tests
tests = [
    # Duration Positive (Strong Anchor)
    {"text": "The initial term of this Agreement is 12 months.", "type": "dur", "expect": True},
    # Duration Positive (Weak Anchor + Context)
    {"text": "This Agreement expires after 2 years.", "type": "dur", "expect": True},
    # Duration Negative (Weak Anchor alone / invalid)
    {"text": "Upon expiry or earlier termination of this agreement.", "type": "dur", "expect": False},
    # Duration Negative (Deadline pattern)
    {"text": "Within 7 days of termination, return all data.", "type": "dur", "expect": False},
    
    # Deadline Positive
    {"text": "Receiving party shall return materials within seven (7) days.", "type": "dline", "expect": True},
    {"text": "Notice must be given no later than 30 days prior.", "type": "dline", "expect": True}
]

failures = 0

for t in tests:
    if t["type"] == "dur":
        res = extract_duration(t["text"])
        found = res["found"]
        status = "PASS" if found == t["expect"] else "FAIL"
        print(f"[DURATION] {status} | '{t['text']}' -> Found={found}")
        if status == "FAIL": failures += 1
    
    elif t["type"] == "dline":
        # Check extraction in 'extract_all_financial_data' if extract_deadlines not imported
        # But for now we might fail if logic isn't there.
        try:
            from documents.financial_utils import extract_deadlines
            res = extract_deadlines(t["text"])
            found = len(res) > 0
            status = "PASS" if found == t["expect"] else "FAIL"
            print(f"[DEADLINE] {status} | '{t['text']}' -> Found={found}")
            if status == "FAIL": failures += 1
        except:
            print(f"[DEADLINE] FAIL | '{t['text']}' -> Function missing")
            failures += 1

if failures == 0:
    print("\nALL TESTS PASSED")
else:
    print(f"\n{failures} TESTS FAILED")
