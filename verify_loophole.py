
import os
import django
import re

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'test_settings')
django.setup()

from documents.loophole_detector import _check_clause_for_patterns

# Mock Clause object
class MockClause:
    def __init__(self, text, id=1):
        self.text = text
        self.id = 1

def test():
    print("Testing loophole detector...")
    
    # Test 1: Should be flagged
    c1 = MockClause("The liability of the party shall be determined without limitation.")
    findings1 = _check_clause_for_patterns(c1, "unlimited_liability")
    print(f"Test 1 (Should match): Found {len(findings1)} match(es)")
    for f in findings1:
        print(f" - {f['matched_text']}")

    # Test 2: Should be IGNORED (Definitional)
    c2 = MockClause("Confidential Information includes without limitation data, codes, and plans.")
    findings2 = _check_clause_for_patterns(c2, "unlimited_liability")
    print(f"Test 2 (Should IGNORE): Found {len(findings2)} match(es)")

    if len(findings1) == 1 and len(findings2) == 0:
        print("SUCCESS: Logic works as expected.")
    else:
        print("FAILURE: Logic did not work as expected.")

if __name__ == "__main__":
    test()
