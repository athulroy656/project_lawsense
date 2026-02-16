
import os
import django
import sys

# Setup Django environment
sys.path.append(r'd:\MAIN_PROJECT')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from documents.vector_utils import collection

print(f"Collection count: {collection.count()}")

try:
    results = collection.query(query_texts=["test"], n_results=1)
    print("Query results:", results)
except Exception as e:
    print(f"Query failed: {e}")
