from sentence_transformers import SentenceTransformer
from chromadb import PersistentClient
from chromadb.config import Settings
from .models import Clause
import os
import logging
import shutil

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHROMA_PATH = os.path.join(BASE_DIR, "chroma_db")

embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

# Lazy initialization - don't create client/collection at module import time
chroma_client = None
collection = None


def _get_collection():
    """
    Lazy initialization of ChromaDB collection with automatic schema recovery.
    This prevents Django from crashing at startup if there's a schema mismatch.
    """
    global chroma_client, collection
    
    if collection is not None:
        return collection
    
    try:
        # Initialize client
        if chroma_client is None:
            chroma_client = PersistentClient(
                path=CHROMA_PATH,
                settings=Settings(anonymized_telemetry=False)
            )
        
        # Try to get or create collection
        collection = chroma_client.get_or_create_collection(name="legal_clauses")
        logger.info("ChromaDB collection initialized successfully")
        return collection
        
    except Exception as e:
        # Check for schema mismatch error
        if "no such column: collections.topic" in str(e):
            logger.warning("--- CHROMA SCHEMA MISMATCH DETECTED ---")
            logger.warning(f"Attempting automatic recovery by recreating database at: {CHROMA_PATH}")
            
            try:
                # Close any existing client
                chroma_client = None
                collection = None
                
                # Backup the old database
                if os.path.exists(CHROMA_PATH):
                    from datetime import datetime
                    backup_name = f"chroma_db_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    backup_path = os.path.join(BASE_DIR, backup_name)
                    shutil.move(CHROMA_PATH, backup_path)
                    logger.info(f"Old database backed up to: {backup_path}")
                
                # Create fresh client and collection
                chroma_client = PersistentClient(
                    path=CHROMA_PATH,
                    settings=Settings(anonymized_telemetry=False)
                )
                collection = chroma_client.get_or_create_collection(name="legal_clauses")
                logger.info("ChromaDB database recreated successfully with correct schema")
                return collection
                
            except Exception as recovery_error:
                logger.critical(f"Failed to automatically recover ChromaDB: {recovery_error}")
                logger.critical(f"Please manually delete the folder: {CHROMA_PATH}")
                logger.critical("Then restart the server.")
                raise recovery_error
        else:
            logger.error(f"Failed to initialize ChromaDB collection: {e}")
            raise e



def index_clauses(document):
    clauses = Clause.objects.filter(document=document)

    if not clauses.exists():
        logger.info("No clauses to index")
        return

    documents = []
    metadatas = []
    ids = []

    for clause in clauses:
        documents.append(clause.text)
        metadata = {
            "document_id": document.id,
            "label": clause.label,
            "clause_id": clause.id,  # Explicitly store clause_id in metadata
        }
        # Add user_id for user-scoped filtering (if document has owner)
        if document.user_id:
            metadata["user_id"] = document.user_id
        metadatas.append(metadata)
        ids.append(str(clause.id))

    _get_collection().add(
        documents=documents,
        metadatas=metadatas,
        ids=ids
    )

    logger.info(f"Indexed {len(documents)} clauses")


def delete_document_from_index(document):
    """
    Remove all embeddings for a given document from the Chroma collection.
    """
    try:
        _get_collection().delete(where={"document_id": document.id})
        logger.info(f"Removed embeddings for document {document.id} from index")
    except Exception as e:
        logger.error(f"Failed to delete embeddings for document {document.id}: {e}")
