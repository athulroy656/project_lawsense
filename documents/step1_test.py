
import sys
import re
from unittest.mock import MagicMock

# Mock dependencies to test logic in isolation
sys.modules["documents.legal_bert_engine"] = MagicMock()
sys.modules["documents.nlp_utils"] = MagicMock()

# Simple mock for split_into_clauses because financial_utils uses it
def mock_split(text):
    return [s.strip() for s in text.split('.') if s.strip()]
sys.modules["documents.nlp_utils"].split_into_clauses = mock_split

from documents.financial_utils import (
    extract_duration,
    extract_liability_caps,
    extract_penalties,
    extract_monetary_amounts,
    extract_expiration_info
)

print("=== STEP 1: False Positive Risk Verification ===\n")

test_cases = [
    {
        "category": "Duration",
        "text": "The initial term of this agreement is 12 months.",
        "expected": "12 months",
        "should_find": True,
        "func": extract_duration
    },
    {
        "category": "Duration (False Positive Risk)",
        "text": "Either party may terminate with a notice period of 30 days.",
        "expected": "None (Should skip notice period)",
        "should_find": False,
        "func": extract_duration
    },
    {
        "category": "Liability Cap",
        "text": "The total liability shall not exceed $5,000.",
        "expected": "$5,000",
        "should_find": True,
        "func": extract_liability_caps
    },
    {
        "category": "Liability Cap (False Positive Risk)",
        "text": "The extracted data size shall not exceed 100MB.",
        "expected": "None (Not financial)",
        "should_find": False,
        "func": extract_liability_caps
    },
     {
        "category": "Penalties",
        "text": "Late payments are subject to an interest of 5% per annum.",
        "expected": "5%",
        "should_find": True,
        "func": extract_penalties
    },
    {
        "category": "Penalties (False Positive Risk)",
        "text": "The Buyer has a controlling interest in the Target Company.",
        "expected": "None (Ownership interest, not penalty)",
        "should_find": False,
        "func": extract_penalties
    }
]

failures = []

for case in test_cases:
    print(f"Testing {case['category']}...")
    print(f"Text: '{case['text']}'")
    
    # Run function
    if case["func"] == extract_penalties:
        # Special handling for list return
        result = case["func"](case["text"])
        found = len(result) > 0
        output = result[0]["amount"] if found else "None"
    elif case["func"] == extract_duration:
        result = case["func"](case["text"])
        found = result["found"]
        output = result["term"] if found else "None"
    elif case["func"] == extract_liability_caps:
        result = case["func"](case["text"])
        found = result["found"]
        output = result["amount"] if found else "None"
    else:
        found = False
        output = "Unknown"

    pass_condition = (found == case["should_find"])
    status = "PASS" if pass_condition else "FAIL"
    
    print(f"Result: {output}")
    print(f"Status: {status}\n")
    
    if not pass_condition:
        failures.append(case)

if failures:
    print(f"\n{len(failures)} Tests Failed!")
    sys.exit(1)
else:
    print("\nAll tests passed!")
