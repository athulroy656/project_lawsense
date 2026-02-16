from django.core.management.base import BaseCommand
from documents.models import Document, Clause
from documents.vector_utils import index_clauses
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Rebuilds ChromaDB embeddings from existing Clause objects in the database.'

    def handle(self, *args, **options):
        documents = Document.objects.all()
        total_docs = documents.count()
        
        self.stdout.write(self.style.SUCCESS(f'Found {total_docs} documents to re-index.'))
        
        success_count = 0
        failure_count = 0
        failed_ids = []

        for i, doc in enumerate(documents, 1):
            clause_count = doc.clauses.count()
            if clause_count == 0:
                self.stdout.write(self.style.WARNING(f'[{i}/{total_docs}] Doc ID {doc.id}: No clauses found. Skipping.'))
                continue

            try:
                self.stdout.write(f'[{i}/{total_docs}] Indexing Doc ID {doc.id} ({clause_count} clauses)...', ending='')
                index_clauses(doc)
                self.stdout.write(self.style.SUCCESS(' DONE'))
                success_count += 1
            except Exception as e:
                self.stdout.write(self.style.ERROR(f' FAILED: {str(e)}'))
                failure_count += 1
                failed_ids.append(doc.id)

        self.stdout.write(self.style.SUCCESS('Re-indexing complete.'))
        self.stdout.write(f'Success: {success_count}')
        self.stdout.write(f'Failed:  {failure_count}')
        
        if failed_ids:
            self.stdout.write(self.style.ERROR(f'Failed Document IDs: {failed_ids}'))
