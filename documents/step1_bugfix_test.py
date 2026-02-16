
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

from documents.financial_utils import (
    extract_expiration_info,
    extract_duration,
    extract_penalties,
    extract_liability_caps
)

print("=== STEP 1 BUGFIX REPRODUCTION ===\n")

# 1. Expiration (Wrong Date / Effective Date)
print("--- [A] Testing Expiration (Expect 31 Dec 2026) ---")
text_exp = "This agreement is effective on 01 January 2025 and shall remain in force until 31 December 2026."
res_exp = extract_expiration_info(text_exp)
print(f"Result: {res_exp['date']}")
if res_exp['date'] == "31 December 2026":
    print("STATUS: PASS")
else:
    print(f"STATUS: FAIL (Found {res_exp['date']})")

# 2. Duration (False Negative on "twelve (12) months")
print("\n--- [B] Testing Duration (Expect 12 months) ---")
text_dur = "The initial term of this agreement is twelve (12) months."
res_dur = extract_duration(text_dur)
print(f"Result: {res_dur['term']}")
if res_dur['found'] and "12" in res_dur['term']:
    print("STATUS: PASS")
else:
    print("STATUS: FAIL")

# 3. Penalties (False Positives)
print("\n--- [C] Testing Penalties (Expect Only ₹5,000) ---")
text_pen = "A penalty of ₹5,000 applies for late payment. This clause does not impose any monetary penalty for other breaches."
res_pen = extract_penalties(text_pen)
print(f"Items Found: {len(res_pen)}")
for p in res_pen:
    print(f" - {p['amount']}: {p['source_text']}")

# We expect exactly 1 penalty (₹5,000). The "no monetary penalty" sentence should be excluded.
valid_penalties = [p for p in res_pen if "₹5,000" in p.get("amount", "")]
if len(valid_penalties) == 1 and len(res_pen) == 1:
    print("STATUS: PASS")
else:
    print("STATUS: FAIL (Expected 1 item with ₹5,000)")

# 4. Liability Cap (Formula/Percent)
print("\n--- [D] Testing Liability Cap (Expect 10% Formula) ---")
text_cap = "Liability shall not exceed ten percent (10%) of the annual fees paid."
res_cap = extract_liability_caps(text_cap)
print(f"Result Amount: {res_cap['amount']}")
# We want to see '10%' or formula indication, not just "Fees paid (Variable)"
if "10%" in str(res_cap['amount']) or "10" in str(res_cap.get('percentage', '')):
    print("STATUS: PASS")
else:
    print("STATUS: FAIL (Likely 'Fees paid (Variable)')")
