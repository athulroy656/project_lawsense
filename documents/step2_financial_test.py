
import sys
import re
from unittest.mock import MagicMock

# Mock dependencies
sys.modules["documents.legal_bert_engine"] = MagicMock()
sys.modules["documents.nlp_utils"] = MagicMock()

def simple_split(text):
    return [text.strip()]

sys.modules["documents.nlp_utils"].split_into_clauses = simple_split

from documents.financial_utils import (
    extract_monetary_amounts, 
    extract_expiration_info, 
    extract_liability_caps,
    extract_penalties
)

print("=== STEP 2: FINANCIAL NORMALIZATION TESTS ===\n")

# Tests Data
tests = [
    # 1. Currency Normalization
    {
        "func": extract_monetary_amounts,
        "text": "The fee is $5,000.00 and EUR 200.",
        "check": lambda res: (
            any(r["currency"] == "USD" and r["value"] == 5000.0 for r in res) and
            any(r["currency"] == "EUR" and r["value"] == 200.0 for r in res)
        ),
        "name": "Currency: USD/EUR Normalization"
    },
    {
        "func": extract_monetary_amounts,
        "text": "Cost is ₹ 10,000 or 10k USD.",
        "check": lambda res: (
            any(r["currency"] == "INR" and r["value"] == 10000.0 for r in res) and
            any(r["currency"] == "USD" and r["value"] == 10000.0 for r in res)
        ),
        "name": "Currency: INR and 'k' suffix"
    },
    
    # 2. Date Normalization
    {
        "func": extract_expiration_info,
        "text": "This agreement expires on 31st December 2026.",
        "check": lambda res: res["iso_date"] == "2026-12-31",
        "name": "Date: 31st December 2026 -> 2026-12-31"
    },
    
    # 3. Liability Caps (Percentage/Formula)
    {
        "func": extract_liability_caps,
        "text": "Liability capped at 10% of annual fees paid.",
        "check": lambda res: (
            res["found"] and 
            res.get("percentage") == 10.0 and 
            "annual fees" in res.get("expression", "").lower()
        ),
        "name": "Cap: Percentage extraction"
    },
    {
        "func": extract_liability_caps,
        "text": "Liability shall not exceed the greater of $10,000 or fees paid.",
        "check": lambda res: (
            res["found"] and 
            res.get("expression") == "greater of $10,000 or fees paid"
        ),
        "name": "Cap: Complex Formula"
    },
    
    # 4. Penalty Cleanliness
    {
        "func": extract_penalties,
        "text": "If late, a penalty of $50 applies. No other penalty.",
        "check": lambda res: len(res) == 1 and res[0]["amount_value"] == 50.0,
        "name": "Penalty: Numeric Only"
    }
]

failures = 0
for t in tests:
    try:
        res = t["func"](t["text"])
        # print(f"DEBUG {t['name']}: {res}")
        if t["check"](res):
            print(f"[PASS] {t['name']}")
        else:
            print(f"[FAIL] {t['name']} - Got: {res}")
            failures += 1
    except Exception as e:
        print(f"[FAIL] {t['name']} - Error: {e}")
        failures += 1

if failures == 0:
    print("\nALL FINANCIAL TESTS PASSED")
else:
    print(f"\n{failures} TESTS FAILED")
