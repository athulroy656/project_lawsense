"""
Ollama LLaMA-3 Integration for LawSense AI
Provides document summarization, risk explanations, and clause interpretation
using locally installed Ollama with LLaMA-3 model.
"""

import ollama
import os
import logging
import hashlib

logger = logging.getLogger(__name__)

# Model configuration - supports llama3, llama3.2, llama2, etc.
# User can set OLLAMA_MODEL environment variable to override
DEFAULT_MODEL = os.getenv("OLLAMA_MODEL", "llama2:7b")

# Check if Ollama is available
OLLAMA_AVAILABLE = True
try:
    ollama.list()
except Exception as e:
    OLLAMA_AVAILABLE = False
    logger.warning(f"Ollama not available: {e}")


def generate_executive_summary(document, detailed=False):
    """
    Generate a 3-paragraph executive summary of the document using local LLaMA-3.
    Uses map-reduce for long documents (>6000 chars) to ensure coverage.
    
    Args:
        document: Document model instance
        detailed (bool): If True, generates a longer output (future feature).
                         Defaults to False (Quick Summary, <250 words).
        
    Returns:
        str: Generated summary text
    """
    if not OLLAMA_AVAILABLE:
        return "AI summary unavailable: Ollama is not running. Please start Ollama service."

    extracted_text = document.extracted_text or ""
    if not extracted_text.strip():
        return "No text content available to summarize."

    full_text_len = len(extracted_text)
    
    # Configuration
    CHUNK_SIZE = 4500
    OVERLAP = 200
    ONE_PASS_LIMIT = 6000

    # Decision: One-Pass vs Map-Reduce
    if full_text_len <= ONE_PASS_LIMIT:
        # --- PATH A: ONE-PASS (Existing behavior) ---
        context_text = extracted_text[:ONE_PASS_LIMIT]
        generation_strategy = "one-pass"
    else:
        # --- PATH B: MAP-REDUCE ---
        generation_strategy = "map-reduce"
        chunks = []
        start = 0
        while start < full_text_len:
            end = min(start + CHUNK_SIZE, full_text_len)
            chunks.append(extracted_text[start:end])
            start += CHUNK_SIZE - OVERLAP
        
        chunk_count = len(chunks)
        logger.info(f"Summary Map-Reduce: Processing {chunk_count} chunks for doc {document.id}")
        
        # Map Phase: Summarize each chunk
        chunk_summaries = []
        for i, chunk in enumerate(chunks):
            try:
                # Basic extraction of key points
                chunk_sum = _summarize_chunk(chunk, i, chunk_count)
                if chunk_sum:
                    chunk_summaries.append(chunk_sum)
            except Exception as e:
                logger.error(f"Failed to summarize chunk {i}: {e}")
        
        # Reduce Phase: Context is the aggregation of chunk summaries
        context_text = "\n\n".join(chunk_summaries)

    # Logging Metrics
    sent_chars = len(context_text)
    try:
        context_hash = hashlib.sha256(context_text.encode('utf-8')).hexdigest()
    except Exception:
        context_hash = "hash_error"
    
    logger.info(f"=== SUMMARY GENERATION [Doc ID: {document.id}] ===")
    logger.info(f"Strategy: {generation_strategy}")
    logger.info(f"Full Text Len: {full_text_len}")
    logger.info(f"Sent Context Len: {sent_chars}")
    logger.info(f"Context Hash: {context_hash[:8]}...")
    logger.info(f"Model: {DEFAULT_MODEL}")
    
    # Final Generation Prompt
    try:
        doc_type = document.get_document_type_display()
    except (AttributeError, TypeError):
        doc_type = getattr(document, 'document_type', 'Unknown')

    if detailed:
        # DETAILED MODE (>400 words)
        length_instr = "Provide a comprehensive analysis (approx. 400-500 words)."
        structure_instr = """
1. **Executive Overview**
[Concise summary of document purpose and scope.]

2. **Key Obligations**
[Detailed breakdown of primary responsibilities for all parties.]

3. **Financial Terms**
[Payment structures, fees, penalties, and refund policies.]

4. **Liability & Indemnification**
[Risk allocation, liability caps, and indemnity clauses.]

5. **Termination & Governance**
[Termination rights, notice periods, governing law, and dispute resolution.]"""
        filter_instr = "Prioritization: Include all material terms, even if standard."
        max_tokens = 800
    else:
        # QUICK MODE (600-900 words)
        length_instr = "Target length: 600–900 words. Must be informative, not generic."
        structure_instr = """
1. **What this is**
[Concise explanation of the document's purpose.]

2. **Key obligations**
[Summary of primary responsibilities.]

3. **Key risks**
[Significant risks or unusual terms.]

4. **Financial/refunds**
[Payment terms, fees, and refund policies.]

5. **Termination/liability**
[How to end the agreement and liability limits.]"""
        filter_instr = "Avoid repeating the same point."
        max_tokens = 800

    prompt = f"""You are a helpful legal assistant explaining a contract to a non-lawyer.
Use plain English. Avoid legal jargon.

Document Type: {doc_type}

Analyze the following document summaries (extracted from key sections) and provide a Plain Summary.

{length_instr}

Format your response exactly as follows:
{structure_instr}

Constraints:
- {length_instr}
- Tone: Professional, direct, authoritative.
- NO filler phrases like "The document is...", "You should be aware...".
- {filter_instr}

Document Key Points Context:
{context_text}

Executive Brief:"""

    try:
        response = ollama.chat(
            model=DEFAULT_MODEL,
            messages=[{
                'role': 'user',
                'content': prompt
            }],
            options={
                'temperature': 0.3,
                'num_predict': max_tokens,
            }
        )
        return response['message']['content']
    except Exception as e:
        logger.error(f"Summary generation failed: {e}")
        return f"AI summary unavailable: {str(e)}"


def _summarize_chunk(chunk_text, chunk_index, total_chunks):
    """
    Helper to extract key legal points from a text chunk.
    """
    prompt = f"""Extract the most important legal points from this document section ({chunk_index + 1}/{total_chunks}).
Focus on: Obligations, Payments, Liability, Termination, Dates, & Rights.
Format: 3-5 bullet points. Be concise.

Text chunk:
{chunk_text}

Key Points:"""

    try:
        response = ollama.chat(
            model=DEFAULT_MODEL,
            messages=[{'role': 'user', 'content': prompt}],
            options={
                'temperature': 0.2, 
                'num_predict': 200, 
                'num_ctx': 4096 
            }
        )
        return response['message']['content']
    except Exception as e:
        logger.warning(f"Chunk summary failed: {e}")
        return ""


def explain_risk(risk_flag, document_text_sample=""):
    """
    Explain why a specific risk flag matters using local LLaMA-3
    
    Args:
        risk_flag: The risk flag text to explain
        document_text_sample: Optional context from the document
        
    Returns:
        str: Plain English explanation of the risk
    """
    prompt = f"""You are a legal analyst explaining legal risks to a non-lawyer.

A legal document analysis flagged this issue:
"{risk_flag}"

Explain in 2-3 sentences:
1. What this means in plain English
2. Why it matters to the user
3. What they should be aware of

Keep it simple, practical, and non-alarming. Do NOT give legal advice.

Explanation:"""

    try:
        if not OLLAMA_AVAILABLE:
            return "AI summary unavailable: Ollama is not running. Please start Ollama service."
            
        response = ollama.chat(
            model=DEFAULT_MODEL,
            messages=[{'role': 'user', 'content': prompt}],
            options={
                'temperature': 0.3,
                'num_predict': 120,
            }
        )
        return response['message']['content']
    except Exception as e:
        return f"Explanation unavailable"


def explain_clause_in_plain_english(clause_text, clause_label=""):
    """
    Translate a legal clause into plain English using local LLaMA-3
    
    Args:
        clause_text: The legal clause text to explain
        clause_label: Optional label/category of the clause
        
    Returns:
        str: Plain English explanation
    """
    label_context = f" (Category: {clause_label})" if clause_label else ""
    
    prompt = f"""You are a legal translator. Explain this legal clause in simple, everyday language that a non-lawyer can understand. Be concise (2-3 sentences max).

Legal clause{label_context}:
"{clause_text}"

Plain English explanation:"""

    try:
        if not OLLAMA_AVAILABLE:
            return "AI summary unavailable: Ollama is not running. Please start Ollama service."
            
        response = ollama.chat(
            model=DEFAULT_MODEL,
            messages=[{'role': 'user', 'content': prompt}],
            options={
                'temperature': 0.3,
                'num_predict': 100,
            }
        )
        return response['message']['content']
    except Exception as e:
        return "Explanation unavailable"


def suggest_improvements(document, risk_flags):
    """
    Suggest practical next steps based on identified risks
    
    Args:
        document: Document model instance
        risk_flags: List of risk flag strings
        
    Returns:
        str: Practical suggestions text
    """
    if not risk_flags:
        return "No significant risks were identified. Review the document for your specific needs."
    
    # Get document type
    try:
        doc_type = document.get_document_type_display()
    except (AttributeError, TypeError):
        doc_type = getattr(document, 'document_type', 'Unknown')
    
    risks_text = "\n".join([f"- {risk}" for risk in risk_flags[:5]])  # Limit to 5 risks
    
    prompt = f"""You are a legal advisor helping someone understand a {doc_type}. Based on the following issues identified:

{risks_text}

Provide 3-4 practical suggestions for what the user should:
1. Ask the other party to clarify
2. Be aware of before agreeing
3. Consider discussing with a legal professional

Be specific and actionable. Use bullet points. Do NOT provide legal advice, only awareness points.

Suggestions:"""

    try:
        if not OLLAMA_AVAILABLE:
            return "AI summary unavailable: Ollama is not running. Please start Ollama service."
            
        response = ollama.chat(
            model=DEFAULT_MODEL,
            messages=[{'role': 'user', 'content': prompt}],
            options={
                'temperature': 0.5,
                'num_predict': 300,
            }
        )
        return response['message']['content']
    except Exception as e:
        return "Suggestions unavailable"


def answer_question_with_context(question, context_clauses, document_type=""):
    """
    Answer a question about a document using relevant clauses as context
    
    Args:
        question: User's question
        context_clauses: List of relevant clause dicts with 'text' and 'label' keys
        document_type: Type of document being analyzed
        
    Returns:
        str: Answer based on the context
    """
    if not context_clauses:
        return "I couldn't find relevant information in the document to answer your question."
    
    # Build context from clauses
    context = "\n\n".join([
        f"Clause ({clause.get('label', 'Unknown')}):\n{clause.get('text', '')}"
        for clause in context_clauses[:4]  # Limit to 4 clauses
    ])
    
    prompt = f"""You are a legal document analyst. Answer the user's question based ONLY on the provided clauses from the document. If the information is not in the provided clauses, say so clearly.

Document Type: {document_type}

Relevant Clauses from the Document:
{context}

User Question: {question}

Instructions:
- Answer based ONLY on what's in the clauses above
- If the answer isn't in the clauses, say "This information is not found in the analyzed portions of the document"
- Be clear and concise
- Do NOT provide legal advice

Answer:"""

    try:
        if not OLLAMA_AVAILABLE:
            return "AI summary unavailable: Ollama is not running. Please start Ollama service."
            
        response = ollama.chat(
            model=DEFAULT_MODEL,
            messages=[{'role': 'user', 'content': prompt}],
            options={
                'temperature': 0.2,  # Very low for factual answers
                'num_predict': 250,
            }
        )
        return response['message']['content']
    except Exception as e:
        return f"Unable to generate answer: {str(e)}"


def test_ollama_connection():
    """
    Test if Ollama is running and accessible
    
    Returns:
        dict: Status and model info
    """
    try:
        if not OLLAMA_AVAILABLE:
            return "AI summary unavailable: Ollama is not running. Please start Ollama service."
            
        response = ollama.chat(
            model=DEFAULT_MODEL,
            messages=[{
                'role': 'user',
                'content': 'Say "LawSense AI connected successfully" in one short sentence.'
            }],
            options={
                'num_predict': 20,
            }
        )
        return {
            "status": "connected",
            "model": DEFAULT_MODEL,
            "response": response['message']['content']
        }
    except Exception as e:
        return {
            "status": "error",
            "model": DEFAULT_MODEL,
            "error": str(e)
        }


def call_ollama(prompt, max_tokens=500, temperature=0.3):
    """
    Generic helper to call Ollama with a prompt.
    Used by other modules (e.g., clause_validator).
    
    Args:
        prompt: The prompt text
        max_tokens: Maximum tokens to generate
        temperature: Temperature for generation (0.0-1.0)
        
    Returns:
        str: Generated response text
    """
    try:
        if not OLLAMA_AVAILABLE:
            raise Exception("Ollama is not running")
            
        response = ollama.chat(
            model=DEFAULT_MODEL,
            messages=[{
                'role': 'user',
                'content': prompt
            }],
            options={
                'temperature': temperature,
                'num_predict': max_tokens,
            }
        )
        return response['message']['content']
    except Exception as e:
        logger.error(f"Ollama call failed: {e}")
        raise

