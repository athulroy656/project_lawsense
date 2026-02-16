
import os
import django
import sys

# Setup Django environment
sys.path.append(r'd:\MAIN_PROJECT')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from documents.qa_utils import answer_question

print("Attempting to answer question...")
try:
    # Use a generic question likely to have matches if any docs exist
    result = answer_question("termination")
    print("Result keys:", result.keys())
    print("Answer snippet:", result.get("answer", "")[:100])
    print("Source clauses count:", len(result.get("source_clauses", [])))
except Exception as e:
    print(f"FAILED: {e}")
    import traceback
    traceback.print_exc()
