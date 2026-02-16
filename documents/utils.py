import pdfplumber
from docx import Document as DocxDocument
import logging

from .models import Document
from .nlp_utils import split_into_clauses
from .clause_rules import classify_clause
from .models import Clause

logger = logging.getLogger(__name__)

def extract_text_from_pdf(file_path):
    text = ""
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text.strip()


def extract_text_from_docx(file_path):
    doc = DocxDocument(file_path)
    return "\n".join([para.text for para in doc.paragraphs]).strip()


def extract_text(file_path):
    if file_path.lower().endswith(".pdf"):
        return extract_text_from_pdf(file_path)
    elif file_path.lower().endswith(".docx"):
        return extract_text_from_docx(file_path)
    else:
        raise ValueError("Unsupported file format")




def process_document(document: Document):
    """
    Process document: extract text from file or validate pasted text
    Note: This function now just extracts text, does not mark as processed
    """
    # If extracted_text already exists (pasted text), just validate and return
    if document.extracted_text and len(document.extracted_text.strip()) > 0:
        logger.info(f"Document {document.id}: Using pasted text ({len(document.extracted_text)} chars)")
        return document.extracted_text
    
    # For file uploads, extract text from file
    if not document.file:
        raise ValueError("No file attached and no text provided")

    logger.info(f"Document {document.id}: Extracting text from file {document.file.path}")
    text = extract_text(document.file.path)
    document.extracted_text = text
    document.save()
    logger.info(f"Document {document.id}: Extracted {len(text)} characters")

    return text

def store_clauses(document):
    clauses = split_into_clauses(document.extracted_text)
    
    # First pass: Regex classification
    clause_objects_data = [] # List of dicts {text, label}
    other_clauses_indices = [] # Indices in clause_objects_data needing BERT check

    for i, c in enumerate(clauses):
        label = classify_clause(c)
        clause_objects_data.append({
            "text": c,
            "label": label
        })
        if label == "Other":
            other_clauses_indices.append(i)

    # Second pass: Batch BERT detection for "Other" clauses
    if other_clauses_indices:
        try:
            from .legal_bert_engine import LegalBertEngine
            engine = LegalBertEngine.get_instance()
            
            # Prepare batch
            texts_to_check = [clause_objects_data[i]["text"] for i in other_clauses_indices]
            
            logger.info(f"Document {document.id}: Batch processing {len(texts_to_check)} clauses with Legal-BERT")
            start_time = __import__('time').time()
            
            implicit_labels = engine.detect_implicit_clauses_batch(texts_to_check)
            
            elapsed = __import__('time').time() - start_time
            logger.info(f"Document {document.id}: Legal-BERT batch finished in {elapsed:.2f}s")

            # Update labels
            for idx, new_label in zip(other_clauses_indices, implicit_labels):
                if new_label:
                    clause_objects_data[idx]["label"] = new_label
                    
        except Exception as e:
            logger.warning(f"Legal-BERT batch detection failed: {e}")

    # Bulk create
    Clause.objects.bulk_create([
        Clause(document=document, text=obj["text"], label=obj["label"])
        for obj in clause_objects_data
    ])
