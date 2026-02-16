import re
from collections import Counter

# Document type detection rules with weighted patterns
# Higher weight = stronger indicator of that document type

DOCUMENT_TYPE_RULES = {
    "NDA_MUTUAL": {
        "patterns": [
            (r"\bmutual\s+(non[- ]?disclosure|nda|confidentiality)\b", 10),
            (r"\bboth\s+parties\s+(agree|shall)\s+(to\s+)?keep\s+confidential\b", 8),
            (r"\beach\s+party\s+(may|shall)\s+disclose\b", 7),
            (r"\breciprocal\s+(confidentiality|disclosure)\b", 8),
            (r"\bdisclosing\s+party.*receiving\s+party\b", 6),
            (r"\bbilateral\s+(agreement|nda)\b", 9),
        ],
        "required": [r"\b(confidential|nda|non[- ]?disclosure)\b"],
    },
    "NDA_ONEWAY": {
        "patterns": [
            (r"\b(one[- ]?way|unilateral)\s+(non[- ]?disclosure|nda|confidentiality)\b", 10),
            (r"\bdiscloser\b.*\brecipient\b", 7),
            (r"\breceiving\s+party\s+(shall|agrees?\s+to|will)\s+(not\s+disclose|keep\s+confidential|maintain)\b", 6),
            (r"\bconfidential\s+information\s+of\s+(the\s+)?disclos(er|ing\s+party)\b", 6),
        ],
        "required": [r"\b(confidential|nda|non[- ]?disclosure)\b"],
        "exclude": [r"\bmutual\b", r"\bbilateral\b", r"\breciprocal\b"],
    },
    "SERVICE_AGREEMENT": {
        "patterns": [
            (r"\bservice\s+agreement\b", 10),
            (r"\bstatement\s+of\s+work\b", 8),
            (r"\bscope\s+of\s+(services|work)\b", 7),
            (r"\bservice\s+provider\b", 6),
            (r"\bconsultant\s+(shall|agrees?|will)\s+(provide|perform|deliver)\b", 6),
            (r"\bdeliverables\b", 5),
            (r"\bproject\s+(milestones?|timeline|schedule)\b", 5),
            (r"\bprofessional\s+services\b", 7),
            (r"\bmaster\s+service\s+agreement\b", 10),
            (r"\b(msa|sow)\b", 6),
            (r"\bhourly\s+rate\b", 4),
            (r"\bservice\s+fees?\b", 5),
        ],
        "required": [r"\b(service|consult|work|deliverable)\b"],
    },
    "PRIVACY_POLICY": {
        "patterns": [
            (r"\bprivacy\s+policy\b", 10),
            (r"\bdata\s+protection\b", 7),
            (r"\bpersonal\s+(data|information)\b", 6),
            (r"\bcollect(s|ing)?\s+(your\s+)?(personal\s+)?(data|information)\b", 6),
            (r"\bgdpr\b", 8),
            (r"\bccpa\b", 8),
            (r"\bdata\s+subject\s+rights?\b", 7),
            (r"\bcookies?\s+(policy|we\s+use)\b", 6),
            (r"\bthird[- ]?party\s+(services?|sharing)\b", 4),
            (r"\bdata\s+retention\b", 6),
            (r"\bright\s+to\s+(access|erasure|rectification|portability)\b", 7),
            (r"\bprocessing\s+(of\s+)?(your\s+)?personal\s+(data|information)\b", 6),
        ],
        "required": [r"\b(privacy|personal\s+(data|information)|data\s+protection)\b"],
    },
    "TERMS_CONDITIONS": {
        "patterns": [
            (r"\bterms\s+(and|&)\s+conditions\b", 10),
            (r"\bterms\s+of\s+(service|use)\b", 10),
            (r"\bacceptable\s+use\s+policy\b", 8),
            (r"\buser\s+agreement\b", 8),
            (r"\bby\s+(using|accessing)\s+(this|our)\s+(website|service|platform)\b", 6),
            (r"\byou\s+agree\s+to\s+(be\s+bound|these\s+terms)\b", 6),
            (r"\baccount\s+(registration|termination)\b", 5),
            (r"\bprohibited\s+(activities|conduct|uses?)\b", 6),
            (r"\buser\s+content\b", 5),
            (r"\bintellectual\s+property\s+rights?\b", 4),
            (r"\bdisclaimer\s+of\s+warranties\b", 5),
        ],
        "required": [r"\b(terms|conditions|user\s+agreement|acceptable\s+use)\b"],
    },
    "EMPLOYMENT_AGREEMENT": {
        "patterns": [
            (r"\bemployment\s+(agreement|contract)\b", 10),
            (r"\bemployee\b.*\bemployer\b", 7),
            (r"\bsalary\b|\bwages?\b|\bcompensation\s+package\b", 6),
            (r"\bjob\s+(title|description|duties)\b", 6),
            (r"\bprobation(ary)?\s+period\b", 7),
            (r"\bworking\s+hours\b", 5),
            (r"\bannual\s+leave\b|\bpaid\s+time\s+off\b|\bpto\b", 6),
            (r"\bbenefits?\s+(package|include)\b", 5),
            (r"\bnon[- ]?compete\b", 6),
            (r"\btermination\s+of\s+employment\b", 7),
            (r"\bnotice\s+period\b", 4),
            (r"\bstart\s+date\b|\bcommencement\s+date\b", 5),
            (r"\bat[- ]?will\s+employment\b", 8),
        ],
        "required": [r"\b(employ(ee|er|ment)|job|salary|wages?)\b"],
    },
}


def detect_document_type(text: str) -> tuple[str, float, dict]:
    """
    Detect document type from extracted text.
    Enhanced with title analysis and boilerplate detection.
    
    Returns:
        tuple: (detected_type, confidence_score, details)
            - detected_type: One of the DOCUMENT_TYPES keys
            - confidence_score: 0.0 to 1.0
            - details: Dict with scores and matched patterns for each type
    """
    text_lower = text.lower()
    scores = {}
    details = {}
    
    # ENHANCEMENT 1: Analyze document title/header (first 150 words)
    first_words = ' '.join(text.split()[:150]).lower()
    title_scores = {
        'NDA_MUTUAL': 0.5 if 'mutual' in first_words and ('non-disclosure' in first_words or 'nda' in first_words) else 0,
        'NDA_ONEWAY': 0.4 if ('non-disclosure agreement' in first_words or 'confidentiality agreement' in first_words) and 'mutual' not in first_words else 0,
        'TERMS_CONDITIONS': 0.5 if ('terms of service' in first_words or 'terms and conditions' in first_words or 'user agreement' in first_words) else 0,
        'SERVICE_AGREEMENT': 0.5 if ('service agreement' in first_words or 'master service' in first_words or 'statement of work' in first_words) else 0,
        'PRIVACY_POLICY': 0.5 if 'privacy policy' in first_words else 0,
        'EMPLOYMENT_AGREEMENT': 0.5 if 'employment agreement' in first_words or 'employment contract' in first_words else 0,
    }
    
    for doc_type, rules in DOCUMENT_TYPE_RULES.items():
        # Check required patterns first
        required = rules.get("required", [])
        has_required = all(
            re.search(pattern, text_lower) for pattern in required
        )
        
        if not has_required:
            scores[doc_type] = 0
            details[doc_type] = {"score": 0, "matched": [], "excluded": False}
            continue
        
        # Check exclusion patterns
        exclude = rules.get("exclude", [])
        is_excluded = any(
            re.search(pattern, text_lower) for pattern in exclude
        )
        
        if is_excluded:
            scores[doc_type] = 0
            details[doc_type] = {"score": 0, "matched": [], "excluded": True}
            continue
        
        # Calculate score from weighted patterns
        type_score = 0
        matched_patterns = []
        
        for pattern, weight in rules["patterns"]:
            matches = re.findall(pattern, text_lower)
            if matches:
                # Cap multiple matches to prevent over-weighting
                match_count = min(len(matches), 3)
                type_score += weight * match_count
                matched_patterns.append({
                    "pattern": pattern,
                    "weight": weight,
                    "count": len(matches)
                })
        
        scores[doc_type] = type_score
        details[doc_type] = {
            "score": type_score,
            "matched": matched_patterns,
            "excluded": False
        }
    
    # ENHANCEMENT 2: Combine pattern scores with title scores
    for doc_type in scores:
        title_bonus = title_scores.get(doc_type, 0)
        if title_bonus > 0:
            # Title match is strong signal, add weighted bonus
            scores[doc_type] = scores[doc_type] * 0.7 + (title_bonus * 30)  # Title can add up to 15 points
            details[doc_type]['title_bonus'] = title_bonus
    
    # Find the highest scoring type
    if not scores or max(scores.values()) == 0:
        return "OTHER", 0.0, details
    
    best_type = max(scores, key=scores.get)
    best_score = scores[best_type]
    
    # Calculate confidence (normalize score)
    # Use a sigmoid-like function to map raw scores to 0-1
    max_reasonable_score = 50  # Expected max score for a strong match
    confidence = min(best_score / max_reasonable_score, 1.0)
    
    # If confidence is too low, return OTHER
    if confidence < 0.15:
        return "OTHER", confidence, details
    
    return best_type, round(confidence, 2), details


def get_document_type_display(doc_type: str) -> str:
    """Get human-readable name for document type."""
    type_names = {
        "NDA_MUTUAL": "NDA (Mutual)",
        "NDA_ONEWAY": "NDA (One-way)",
        "SERVICE_AGREEMENT": "Service Agreement",
        "PRIVACY_POLICY": "Privacy Policy",
        "TERMS_CONDITIONS": "Terms & Conditions",
        "EMPLOYMENT_AGREEMENT": "Employment Agreement",
        "OTHER": "Other/Unknown",
    }
    return type_names.get(doc_type, "Other/Unknown")
