
import sys
from unittest.mock import MagicMock, patch

# Mock dependencies
sys.modules["documents.legal_bert_engine"] = MagicMock()
sys.modules["documents.vector_utils"] = MagicMock()
sys.modules["documents.models"] = MagicMock()
sys.modules["documents.ollama_utils"] = MagicMock()
sys.modules["langchain_core"] = MagicMock()
sys.modules["langchain_core.documents"] = MagicMock()
# Mock Document class inside langchain_core
class MockLCDoc:
    def __init__(self, page_content, metadata):
        self.page_content = page_content
        self.metadata = metadata
sys.modules["langchain_core.documents"].Document = MockLCDoc

sys.modules["documents.nlp_utils"] = MagicMock()
mock_nlp = sys.modules["documents.nlp_utils"]

# Simple mock for split
def simple_split(text):
    return [s.strip() for s in text.split('.') if s.strip()]

mock_nlp.split_into_clauses = simple_split

# Setup mocks
mock_models = sys.modules["documents.models"]

mock_vector = sys.modules["documents.vector_utils"]
mock_ollama = sys.modules["documents.ollama_utils"]

# Mock Document and Clause
class MockDocument:
    def __init__(self, id, text):
        self.id = id
        self.extracted_text = text

class MockClause:
    def __init__(self, id, text, label, doc_id):
        self.id = id
        self.text = text
        self.label = label
        self.document_id = doc_id
        self.metadata = {"document_id": doc_id} 

# Mock Document Manager
mock_doc_store = {}
def get_doc(id):
    return mock_doc_store.get(id)

mock_models.Document.objects.get.side_effect = get_doc

# Import AFTER mocking
from documents.financial_utils import extract_all_financial_data
from documents.qa_utils import answer_question

print("=== STEP 1 Extension: Financial Data & Q&A Test ===\n")

# --- Test 1: Extraction Logic ---
print("--- [A] Testing extract_all_financial_data ---")
samples = [
    {
        "text": "liability shall not exceed 10% of annual fees paid",
        "check": lambda d: d["liability_cap"]["found"] and "Fees paid" in d["liability_cap"]["amount"]
    },
    {
        "text": "liability shall not exceed $5,000",
        "check": lambda d: d["liability_cap"]["found"] and "$5,000" in d["liability_cap"]["amount"]
    },
    {
        "text": "penalty of ₹5,000 applies if payment is delayed beyond 30 days",
        "check": lambda d: len(d["penalties"]) > 0 and "₹5,000" in d["penalties"][0]["amount"]
    },
    {
        "text": "remain in force until 31 December 2026",
        "check": lambda d: d["expiration"]["found"] and "31 December 2026" in d["expiration"]["date"]
    },
    {
        "text": "initial term is 12 months",
        "check": lambda d: d["duration"]["found"] and "12 months" in d["duration"]["term"]
    },
    {
        "text": "notice period of 30 days",
        "check": lambda d: not d["duration"]["found"] # Negative test
    }
]

for i, s in enumerate(samples):
    res = extract_all_financial_data(s["text"])
    if s["check"](res):
        print(f"Test {i+1} PASS")
    else:
        print(f"Test {i+1} FAIL. Result: {res}")

# --- Test 2: Q&A Determinism ---
print("\n--- [B] Testing Deterministic Q&A ---")

# Setup mock document
doc_text = "The total liability of the Provider is capped at $50,000. The term is 2 years."
doc_id = 99
mock_doc = MockDocument(doc_id, doc_text)
mock_doc_store[doc_id] = mock_doc

# Setup mock retrieval
# retrieve_clauses returns list of objects with metadata
class MockRetrievedDoc:
    def __init__(self, doc_id):
        self.metadata = {"document_id": doc_id}

# Patch retrieve_clauses in qa_utils
with patch('documents.qa_utils.retrieve_clauses') as mock_retrieve:
    # Scenario 1: Ask about liability
    mock_retrieve.return_value = [MockRetrievedDoc(doc_id)]
    
    q1 = "What is the maximum liability?"
    ans1 = answer_question(q1)
    
    if ans1 and "liability cap of **$50,000**" in ans1["answer"] and "Derived from deterministic" in ans1["answer"]:
        print(f"Q&A Test 1 (Liability) PASS: {ans1['answer'][:50]}...")
    else:
        print(f"Q&A Test 1 (Liability) FAIL: {ans1}")

    # Scenario 2: Ask about duration
    q2 = "How long is the term?"
    ans2 = answer_question(q2)
    
    if ans2 and "Duration: 2 years" in ans2["answer"]:
        print(f"Q&A Test 2 (Duration) PASS: {ans2['answer'][:50]}...")
    else:
        print(f"Q&A Test 2 (Duration) FAIL: {ans2}")

    # Scenario 3: Irrelevant question (Fallback to None/RAG - here None because internal RAG logic mocked out/fails)
    q3 = "Who is the CEO?"
    # We expect the deterministic block to SKIP.
    # Since we didn't mock the rest of answer_question fully (Clause lookup etc), it might fail or return standard msg.
    # We just want to ensure it DOES NOT return structured finance data.
    ans3 = answer_question(q3)
    
    if "Derived from deterministic" not in str(ans3):
        print("Q&A Test 3 (Non-financial) PASS: Correctly skipped deterministic block")
    else:
        print(f"Q&A Test 3 (Non-financial) FAIL: {ans3}")

print("\nTests Complete.")
