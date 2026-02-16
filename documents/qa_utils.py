import os
import re
from langchain_core.documents import Document as LCDocument
from documents.vector_utils import _get_collection
from documents.ollama_utils import answer_question_with_context
from documents.models import Clause, Document
from documents.financial_utils import extract_all_financial_data


# Check if Ollama should be used (default: True for local LLM)
USE_OLLAMA = os.getenv("USE_OLLAMA", "true").lower() == "true"


def retrieve_clauses(question, document_id, user_id=None, n_results=4):
    """
    Retrieve relevant clauses using vector similarity search
    SECURITY: Filters by document_id and optionally user_id to prevent cross-document leakage
    
    Args:
        question: User's question
        document_id: ID of the document to search within
        user_id: Optional user ID for additional filtering
        n_results: Number of results to return
    """
    # Build metadata filter for document isolation
    if user_id is not None:
        # ChromaDB requires "$and" operator for multiple metadata filters
        where_filter = {
            "$and": [
                {"document_id": document_id},
                {"user_id": user_id}
            ]
        }
    else:
        where_filter = {"document_id": document_id}
    
    results = _get_collection().query(
        query_texts=[question],
        n_results=n_results,
        where=where_filter  # CRITICAL: Filter by document_id and user_id
    )

    docs = []
    # Zip documents, metadatas, AND ids
    if results.get("ids") and results.get("documents") and results.get("metadatas"):
        for text, meta, id_ in zip(results["documents"][0], results["metadatas"][0], results["ids"][0]):
            # Ensure metadata is a dict (sometimes it can be None in Chroma if not set)
            if meta is None:
                meta = {}
            
            # The Chroma ID is the Clause ID (as set in vector_utils.index_clauses)
            # Inject it into metadata so downstream code can find it
            meta['clause_id'] = id_
            
            docs.append(
                LCDocument(
                    page_content=text,
                    metadata=meta
                )
            )
    return docs


def rerank_by_keywords(question, candidate_clauses, top_k=3):
    """
    Re-rank vector search results by keyword overlap for better relevance
    
    Args:
        question: User's question
        candidate_clauses: List of Clause objects from vector search
        top_k: Number of top results to return
    
    Returns:
        list: Re-ranked Clause objects
    """
    # Extract keywords from question (remove common stop words)
    question_words = set(re.findall(r'\b\w+\b', question.lower()))
    stop_words = {'what', 'how', 'when', 'where', 'why', 'who', 'can', 'i', 'the', 'is', 'are', 
                  'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with'}
    question_words = question_words - stop_words
    
    if not question_words:
        return candidate_clauses[:top_k]
    
    scored_clauses = []
    for clause in candidate_clauses:
        clause_words = set(re.findall(r'\b\w+\b', clause['text'].lower()))
        
        # Calculate keyword overlap
        overlap = len(question_words & clause_words)
        overlap_score = overlap / len(question_words) if question_words else 0
        
        scored_clauses.append((overlap_score, clause))
    
    # Sort by score (descending)
    scored_clauses.sort(reverse=True, key=lambda x: x[0])
    
    return [clause for score, clause in scored_clauses[:top_k]]


def calculate_confidence(question, clauses):
    """
    Calculate answer confidence based on relevance of retrieved clauses
    
    Returns:
        float: Confidence score 0.0 to 1.0
    """
    question_words = set(re.findall(r'\b\w+\b', question.lower()))
    stop_words = {'what', 'how', 'when', 'where', 'why', 'who', 'can', 'i', 'the', 'is', 'are'}
    question_words = question_words - stop_words
    
    if not question_words or not clauses:
        return 0.3
    
    # Check keyword overlap with top clause
    top_clause_words = set(re.findall(r'\b\w+\b', clauses[0]['text'].lower()))
    overlap = len(question_words & top_clause_words)
    confidence = min(overlap / len(question_words), 1.0)
    
    return round(confidence, 2)


def answer_question(question, document_id, user_id=None, document_type=""):
    """
    Answer a question using vector search + re-ranking + local Ollama LLaMA-3
    Enhanced with citations and confidence scores
    SECURITY: Scoped to a specific document_id to prevent cross-document leakage
    
    Args:
        question: User's question
        document_id: ID of the document to query (REQUIRED)
        user_id: Optional user ID for additional filtering
        document_type: Type of document being analyzed (optional)
        
    Returns:
        dict or str: Enhanced answer with citations or simple string
    """
    # Step 1: Vector search for initial candidates (SCOPED to document_id)
    docs = retrieve_clauses(question, document_id=document_id, user_id=user_id, n_results=5)

    # --- DETERMINISTIC FINANCIAL DATA CHECK ---
    financial_keywords = ["liability", "cap", "limit", "penalty", "fine", "expiration", "expire", "valid until", "term", "duration"]
    # Check if this is a financial question
    if any(kw in question.lower() for kw in financial_keywords):
        try:
            # Use the provided document_id directly (already scoped to this document)
            doc_obj = Document.objects.get(id=document_id)
            fin_data = extract_all_financial_data(doc_obj.extracted_text)
            
            # 3. Check for specific intent match
            q_lower = question.lower()
            structured_answer = None
            source_text = "See document details."

            # Intent: Liability
            if "liability" in q_lower or "cap" in q_lower or "limit" in q_lower:
                cap = fin_data.get("liability_cap", {})
                if cap.get("found"):
                    amount = cap.get("amount")
                    structured_answer = f"According to the structured analysis, this document contains a liability cap of **{amount}**."
                    source_text = cap.get("source") or source_text
            
            # Intent: Penalties
            elif ("penalty" in q_lower or "fine" in q_lower) and not structured_answer:
                penalties = fin_data.get("penalties", [])
                if penalties:
                    items = [f"- {p.get('amount')} ({p.get('condition')})" for p in penalties]
                    structured_answer = "The analysis detected the following penalty clauses:\n" + "\n".join(items)
                    if penalties: source_text = penalties[0].get("source")

            # Intent: Expiration/Term
            elif ("expire" in q_lower or "valid" in q_lower or "term" in q_lower or "duration" in q_lower) and not structured_answer:
                 exp = fin_data.get("expiration", {})
                 dur = fin_data.get("duration", {})
                 parts = []
                 
                 if exp.get("found"):
                     parts.append(f"**Expiration Date:** {exp.get('date')}")
                     source_text = exp.get("source")
                 if dur.get("found"):
                     parts.append(f"**Duration:** {dur.get('term')}")
                     if not source_text or source_text == "See document details.": 
                         source_text = dur.get("source")
                 
                 if parts:
                     structured_answer = " | ".join(parts)

            # 4. Return if we found a structured answer
            if structured_answer:
                return {
                    "answer": structured_answer + "\n\n*(Derived from deterministic financial analysis)*",
                    "source_clauses": [{
                        'id': 0, 
                        'label': 'Financial Extraction', 
                        'text': source_text
                    }],
                    "confidence": 1.0
                }
        except Exception as e:
            # Fallback to standard RAG if anything fails (e.g. Doc lookup)
            pass
    # ------------------------------------------

    if not docs:
        return {"answer": "No relevant clauses found in the document.", "source_clauses": [], "confidence": 0.0}
    
    # Step 2: Convert to clause objects for re-ranking
    candidate_clauses = []
    for doc in docs:
        clause_id = doc.metadata.get('clause_id')
        if clause_id:
            try:
                clause = Clause.objects.get(id=clause_id)
                candidate_clauses.append({
                    'id': clause.id,
                    'text': clause.text,
                    'label': clause.label
                })
            except Clause.DoesNotExist:
                pass
    
    if not candidate_clauses:
        return {"answer": "No relevant clauses found in the document.", "source_clauses": [], "confidence": 0.0}
    
    # Step 3: Re-rank by keyword relevance
    reranked_clauses = rerank_by_keywords(question, candidate_clauses, top_k=3)
    
    # Format for display
    context_display = "\n\n".join(
        f"- [{clause['label']}] {clause['text'][:300]}..." for clause in reranked_clauses
    )

    # If Ollama is disabled, return raw clauses with citations
    if not USE_OLLAMA:
        return {
            "answer": f"**Relevant clauses found:**\n\n{context_display}",
            "source_clauses": [
                {
                    'id': clause['id'],
                    'label': clause['label'],
                    'text': clause['text'][:200] + ('...' if len(clause['text']) > 200 else '')
                }
                for clause in reranked_clauses
            ],
            "confidence": calculate_confidence(question, reranked_clauses)
        }

    # Step 4: Use Ollama LLaMA-3 for intelligent answer with enhanced context
    try:
        # Build enhanced context with clause numbers
        context_parts = []
        for i, clause in enumerate(reranked_clauses, 1):
            context_parts.append(f"[CLAUSE {i}] (Type: {clause['label']})\n{clause['text']}")
        
        enhanced_context = "\n\n".join(context_parts)
        
        # Enhanced prompt for better answers
        prompt = f"""You are analyzing a legal document. Answer the user's question based ONLY on the provided clauses.

QUESTION: {question}

RELEVANT CLAUSES:
{enhanced_context}

INSTRUCTIONS:
1. Answer in plain English (no legal jargon unless necessary)
2. Reference specific clause numbers when citing (e.g., "According to Clause 1...")
3. If the document doesn't address the question, say "This document doesn't cover that topic"
4. Highlight any concerning or one-sided language you see
5. Keep answer under 150 words
6. Be direct and specific

ANSWER:"""
        
        # Prepare clauses for Ollama function
        context_clauses = [
            {
                "text": clause['text'],
                "label": clause['label']
            }
            for clause in reranked_clauses
        ]
        
        answer_text = answer_question_with_context(
            question=question,
            context_clauses=context_clauses,
            document_type=document_type
        )
        
        # Return enhanced response with citations
        return {
            "answer": answer_text,
            "source_clauses": [
                {
                    'id': clause['id'],
                    'label': clause['label'],
                    'text': clause['text'][:200] + ('...' if len(clause['text']) > 200 else '')
                }
                for clause in reranked_clauses
            ],
            "confidence": calculate_confidence(question, reranked_clauses)
        }
        
    except Exception as e:
        # Fallback to showing raw clauses with citations if Ollama fails
        return {
            "answer": f"**AI answer unavailable. Relevant clauses:**\n\n{context_display}",
            "source_clauses": [
                {
                    'id': clause['id'],
                    'label': clause['label'],
                    'text': clause['text'][:200] + ('...' if len(clause['text']) > 200 else '')
                }
                for clause in reranked_clauses
            ],
            "confidence": calculate_confidence(question, reranked_clauses)
        }
