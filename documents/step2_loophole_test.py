
import sys
from unittest.mock import MagicMock, patch

# Mock Django models
sys.modules["documents.models"] = MagicMock()
from documents.models import Clause, Document

# Mock the module under test
import documents.loophole_detector as ld

# Helper to create a mock document
def create_mock_doc(doc_type, text):
    doc = MagicMock()
    doc.document_type = doc_type
    doc.extracted_text = text
    return doc

# Helper to mock Clause.objects.filter
def mock_clauses(clauses_list):
    mock_qs = MagicMock()
    mock_qs.exists.return_value = len(clauses_list) > 0
    mock_qs.__iter__.return_value = iter(clauses_list)
    return mock_qs

print("=== STEP 2: CONTEXT-AWARE LOOPHOLE DETECTION TEST ===\n")

# TEST 1: NDA Missing Permitted Disclosure
print("[TEST 1] NDA Missing Permitted Disclosure")
doc_nda = create_mock_doc("NDA_MUTUAL", "This is a mutual NDA. Confidential info shall be kept secret.")
# No clauses found
with patch("documents.loophole_detector.Clause.objects.filter", return_value=mock_clauses([])):
    findings = ld._check_missing_clauses(doc_nda)
    
    # Check if "Missing Permitted Disclosure" is in findings
    found = any(f["category"] == "Missing Permitted Disclosure" for f in findings)
    print(f"Result: {'PASS' if found else 'FAIL'} (Expected Found)")
    if not found:
        print("Findings:", [f["category"] for f in findings])

# TEST 2: NDA With Permitted Disclosure (Should NOT flag)
print("\n[TEST 2] NDA With Permitted Disclosure")
doc_nda_good = create_mock_doc("NDA_MUTUAL", "This NDA allows permitted disclosure to employees on a need to know basis.")
with patch("documents.loophole_detector.Clause.objects.filter", return_value=mock_clauses([])):
    findings = ld._check_missing_clauses(doc_nda_good)
    
    found = any(f["category"] == "Missing Permitted Disclosure" for f in findings)
    print(f"Result: {'PASS' if not found else 'FAIL'} (Expected NOT Found)")

# TEST 3: Employment Missing IP Assignment
print("\n[TEST 3] Employment Missing IP Assignment")
doc_emp = create_mock_doc("EMPLOYMENT_AGREEMENT", "You are hired as a dev. Salary is 100k.")
with patch("documents.loophole_detector.Clause.objects.filter", return_value=mock_clauses([])):
    findings = ld._check_missing_clauses(doc_emp)
    
    found = any(f["category"] == "Missing IP/Invention Assignment" for f in findings)
    print(f"Result: {'PASS' if found else 'FAIL'} (Expected Found)")

# TEST 4: Global Check (Force Majeure) on Random Doc
print("\n[TEST 4] Global Force Majeure Check")
doc_other = create_mock_doc("OTHER", "Just some random text.")
with patch("documents.loophole_detector.Clause.objects.filter", return_value=mock_clauses([])):
    findings = ld._check_missing_clauses(doc_other)
    
    found = any(f["category"] == "Missing Force Majeure Clause" for f in findings)
    print(f"Result: {'PASS' if found else 'FAIL'} (Expected Found)")

print("\n=== TEST COMPLETE ===")
