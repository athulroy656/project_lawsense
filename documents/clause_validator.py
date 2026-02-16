"""
Semantic clause validation using LLM.
This module provides fallback validation when regex-based detection fails.
"""

import json
import logging

logger = logging.getLogger(__name__)

# Key structural clauses that benefit from semantic fallback
KEY_STRUCTURAL_CLAUSES = {
    "Limitation of Liability": "Clause that limits or caps the maximum liability or damages one party can claim from another.",
    "Indemnification": "Clause requiring one party to compensate or defend the other party against losses, damages, or legal claims.",
    "Termination": "Clause specifying the conditions, procedures, or rights under which the agreement can be terminated or ended.",
    "Governing Law": "Clause identifying which jurisdiction's laws will govern the interpretation and enforcement of the agreement.",
    "Dispute Resolution": "Clause specifying how disputes will be resolved, including arbitration, mediation, or litigation procedures.",
    "Arbitration": "Clause requiring disputes to be resolved through arbitration rather than court litigation.",
    "Confidentiality": "Clause requiring parties to keep certain information confidential and not disclose it to third parties.",
    "Force Majeure": "Clause excusing performance obligations when prevented by unforeseeable circumstances beyond a party's control.",
    "Severability": "Clause stating that if any provision is found invalid or unenforceable, the remaining provisions remain in effect.",
    "Entire Agreement": "Clause stating that the written agreement constitutes the complete understanding and supersedes all prior agreements.",
}


def validate_clause_match(clause_name, paragraph_text):
    """
    Validate whether a paragraph represents a specific clause using LLM.
    
    Args:
        clause_name: Name of the clause to validate (e.g., "Termination")
        paragraph_text: The text paragraph to validate
        
    Returns:
        dict: {
            "status": "VALID_MATCH" | "POSSIBLE_MATCH" | "NOT_A_MATCH",
            "confidence": float (0.0-1.0),
            "evidence": list of quoted phrases,
            "reason": str
        }
    """
    # Get clause description
    clause_description = KEY_STRUCTURAL_CLAUSES.get(
        clause_name, 
        f"Clause related to {clause_name}"
    )
    
    # Build validation prompt
    prompt = f"""You are validating whether a retrieved paragraph represents a specific legal clause.

CRITICAL RULES:
- Use ONLY the provided paragraph.
- Do NOT assume missing language.
- Do NOT hallucinate.
- Be conservative.
- If uncertain, choose "POSSIBLE_MATCH".
- If the clause is clearly not present, choose "NOT_A_MATCH".

CLAUSE TO VALIDATE:
Name: {clause_name}

Description:
{clause_description}

PARAGRAPH:
\"\"\"
{paragraph_text}
\"\"\"

TASK:
Determine whether the paragraph clearly contains the specified clause.

Definitions:
VALID_MATCH → The paragraph explicitly contains language matching the clause description.
POSSIBLE_MATCH → The paragraph is related but indirect, partial, or ambiguous.
NOT_A_MATCH → The paragraph does not meaningfully represent the clause.

Return ONLY valid JSON in the following exact format:

{{
  "status": "VALID_MATCH" | "POSSIBLE_MATCH" | "NOT_A_MATCH",
  "confidence": 0.0,
  "evidence": ["<direct short quote from paragraph>"],
  "reason": "<one short sentence explanation>"
}}

OUTPUT RULES:
- confidence must be a number between 0.0 and 1.0.
- evidence must contain direct phrases copied from the paragraph (max 12 words each).
- If NOT_A_MATCH, evidence must be an empty list [].
- Do not include any extra text outside the JSON.
"""
    
    try:
        # Use Ollama for validation (same as existing AI summary generation)
        from .ollama_utils import OLLAMA_AVAILABLE, call_ollama
        
        if not OLLAMA_AVAILABLE:
            logger.warning("Ollama not available for clause validation")
            return {
                "status": "NOT_A_MATCH",
                "confidence": 0.0,
                "evidence": [],
                "reason": "LLM validation unavailable"
            }
        
        # Call LLM with validation prompt
        response = call_ollama(prompt, max_tokens=300, temperature=0.1)
        
        # Parse JSON response
        # Extract JSON from response (handle markdown code blocks)
        response_text = response.strip()
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()
        
        result = json.loads(response_text)
        
        # Validate result structure
        required_keys = {"status", "confidence", "evidence", "reason"}
        if not required_keys.issubset(result.keys()):
            raise ValueError(f"Missing required keys in LLM response: {required_keys - result.keys()}")
        
        # Validate status value
        valid_statuses = {"VALID_MATCH", "POSSIBLE_MATCH", "NOT_A_MATCH"}
        if result["status"] not in valid_statuses:
            raise ValueError(f"Invalid status: {result['status']}")
        
        # Validate confidence range
        if not (0.0 <= result["confidence"] <= 1.0):
            result["confidence"] = max(0.0, min(1.0, result["confidence"]))
        
        return result
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM validation response: {e}")
        return {
            "status": "NOT_A_MATCH",
            "confidence": 0.0,
            "evidence": [],
            "reason": "Failed to parse validation response"
        }
    except Exception as e:
        logger.error(f"Clause validation error: {e}")
        return {
            "status": "NOT_A_MATCH",
            "confidence": 0.0,
            "evidence": [],
            "reason": f"Validation error: {str(e)}"
        }


def should_use_semantic_fallback(clause_label):
    """
    Determine if a clause should use semantic fallback when regex fails.
    
    Args:
        clause_label: The clause label to check
        
    Returns:
        bool: True if semantic fallback should be used
    """
    return clause_label in KEY_STRUCTURAL_CLAUSES
