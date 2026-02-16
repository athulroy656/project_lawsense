import spacy
import re

# Load SpaCy model once (important for performance)
nlp = spacy.load("en_core_web_sm")


def preprocess_pdf_text(text: str) -> str:
    """
    Clean and normalize PDF-extracted text for better sentence detection.
    """
    # Replace multiple newlines with paragraph marker
    text = re.sub(r'\n{2,}', '\n\n', text)
    
    # Join lines that don't end with sentence-ending punctuation
    # This fixes mid-sentence line breaks common in PDFs
    lines = text.split('\n')
    joined_lines = []
    current_line = ""
    
    for line in lines:
        line = line.strip()
        if not line:
            if current_line:
                joined_lines.append(current_line)
                current_line = ""
            joined_lines.append("")  # Keep paragraph break
            continue
        
        if current_line:
            # Check if current_line ends with sentence-ending punctuation
            if current_line[-1] in '.!?:':
                joined_lines.append(current_line)
                current_line = line
            else:
                # Join with space (mid-sentence line break)
                current_line = current_line + " " + line
        else:
            current_line = line
    
    if current_line:
        joined_lines.append(current_line)
    
    return '\n'.join(joined_lines)


def has_legal_content(text: str) -> bool:
    """
    Check if a short text segment contains legal terminology.
    """
    legal_keywords = [
        'shall', 'must', 'agree', 'term', 'condition', 'liability',
        'warrant', 'indemnif', 'terminat', 'govern', 'law', 'right',
        'obligat', 'restrict', 'permit', 'prohibit', 'disclaim',
        'license', 'licence', 'property', 'intellectual', 'confidential'
    ]
    text_lower = text.lower()
    return any(kw in text_lower for kw in legal_keywords)


def split_by_paragraphs(text: str) -> list:
    """
    Fallback: split by paragraphs when SpaCy sentence detection fails.
    """
    paragraphs = text.split('\n\n')
    clauses = []
    
    for para in paragraphs:
        para = para.strip()
        # Skip very short paragraphs
        if len(para) > 50:
            clauses.append(para)
        elif len(para) > 20 and has_legal_content(para):
            clauses.append(para)
    
    return clauses


def split_into_clauses(text: str):
    """
    Split extracted document text into clause-like sentences.
    Handles PDF text with unusual formatting.
    """
    # Preprocess PDF text to fix line breaks
    cleaned_text = preprocess_pdf_text(text)
    
    # Use SpaCy for sentence detection
    doc = nlp(cleaned_text)
    clauses = []

    for sent in doc.sents:
        cleaned = sent.text.strip()
        # Filter out very short segments (noise/headers)
        # But keep segments with legal keywords even if shorter
        if len(cleaned) > 50:
            clauses.append(cleaned)
        elif len(cleaned) > 20 and has_legal_content(cleaned):
            clauses.append(cleaned)
    
    # If SpaCy found very few clauses, try paragraph-based splitting
    if len(clauses) < 5:
        clauses = split_by_paragraphs(cleaned_text)
    
    return clauses
