from collections import Counter
from .models import Clause
from .clause_rules import CLAUSE_RULES
from .loophole_detector import detect_loopholes
from .favorability_analysis import (
    analyze_clause_favorability,
    detect_asymmetry,
    generate_favorability_summary
)
from .clause_importance import categorize_missing_clauses


# =========================================================
# INVERTED PYRAMID: Scoring & Synthesis Functions
# =========================================================

def calculate_safety_score(summary_data, favorability, asymmetries, loopholes):
    """Calculate a safety score from 0.0 to 10.0 (10 = safest)
    
    IMPORTANT: Be conservative with penalties. Missing clauses alone
    should NOT cause a document to be marked as "high risk".
    Only actual problematic content should significantly lower the score.
    """
    score = 10.0
    
    # Penalty for rule-based risks - be gentle with "Missing" items
    for r in summary_data.get("risks", []):
        if "Missing" in r:
            score -= 0.1  # Very minor penalty - missing isn't necessarily bad
        else:
            score -= 0.8  # Moderate penalty for actual issues
    
    # Penalty for unfavorable terms - only significant ones matter
    if favorability and isinstance(favorability, dict):
        score -= favorability.get("high_risk_count", 0) * 0.5
        score -= favorability.get("medium_risk_count", 0) * 0.2
    
    # Penalty for asymmetries - these are more concerning
    if asymmetries and isinstance(asymmetries, list):
        for asym in asymmetries:
            if isinstance(asym, dict):
                score -= 0.5 if asym.get("severity") == "HIGH" else 0.25
    
    # Penalty for loopholes - handle both dict and list formats
    if loopholes:
        loophole_list = []
        if isinstance(loopholes, dict):
            loophole_list = loopholes.get("loopholes", [])
        elif isinstance(loopholes, list):
            loophole_list = loopholes
        
        for lp in loophole_list:
            if isinstance(lp, dict):
                sev = lp.get("severity", "").upper()
                if sev == "CRITICAL": score -= 1.0
                elif sev == "HIGH": score -= 0.5
                elif sev == "MEDIUM": score -= 0.25
    
    # Ensure minimum score of 3.0 - nothing should be "catastrophic"
    # Most real-world T&Cs are usable even with concerns
    return max(round(score, 1), 3.0)


def get_exposure_level(score):
    """
    Map safety score to exposure level.
    Score ranges: 10.0 (safest) to 3.0 (highest risk)
    """
    if score >= 8.0:
        return "Low"
    elif score >= 6.5:
        return "Moderate"
    elif score >= 5.0:
        return "Elevated"
    else:
        return "High"


def generate_top_factors(summary_data, favorability, asymmetries, loopholes):
    """
    Generate top 3 contributing factors from analysis results.
    Returns list of human-readable factor descriptions.
    """
    factors = []
    
    # Factor 1: Loopholes (highest priority)
    if loopholes:
        loophole_list = []
        if isinstance(loopholes, dict):
            loophole_list = loopholes.get("loopholes", [])
        elif isinstance(loopholes, list):
            loophole_list = loopholes
        
        critical_loopholes = [lp for lp in loophole_list if isinstance(lp, dict) and lp.get("severity") == "CRITICAL"]
        high_loopholes = [lp for lp in loophole_list if isinstance(lp, dict) and lp.get("severity") == "HIGH"]
        
        if critical_loopholes:
            factors.append(f"Critical issue: {critical_loopholes[0].get('category', 'Problematic clause detected')}")
        elif high_loopholes:
            factors.append(f"High-risk pattern: {high_loopholes[0].get('category', 'Concerning clause found')}")
    
    # Factor 2: Asymmetries
    if asymmetries and isinstance(asymmetries, list):
        high_asymmetries = [a for a in asymmetries if isinstance(a, dict) and a.get("severity") == "HIGH"]
        if high_asymmetries and len(factors) < 3:
            factors.append(f"One-sided terms: {high_asymmetries[0].get('category', 'Imbalanced obligations')}")
    
    # Factor 3: Unfavorable terms
    if favorability and isinstance(favorability, dict):
        high_risk_count = favorability.get("high_risk_count", 0)
        if high_risk_count > 0 and len(factors) < 3:
            factors.append(f"{high_risk_count} clause{'s' if high_risk_count > 1 else ''} heavily favor the provider")
    
    # Factor 4: Missing critical clauses
    if len(factors) < 3:
        missing_critical = summary_data.get("missing_critical", [])
        if missing_critical:
            factors.append(f"Missing {len(missing_critical)} critical protection{'s' if len(missing_critical) > 1 else ''}")
    
    # Factor 5: General risks
    if len(factors) < 3:
        risks = summary_data.get("risks", [])
        non_missing_risks = [r for r in risks if "Missing" not in r]
        if non_missing_risks:
            factors.append(non_missing_risks[0])
    
    # Ensure we have at least 1 factor
    if not factors:
        factors.append("Standard terms with minor concerns")
    
    # Return top 3
    return factors[:3]


def generate_overall_assessment(exposure_level, top_factors, clause_coverage, doc_type_confidence):
    """
    Generate deterministic assessment text based on exposure level and factors.
    Does NOT use raw document text or LLM.
    """
    found = clause_coverage.get("found", 0)
    expected = clause_coverage.get("expected", 0)
    coverage_pct = (found / expected * 100) if expected > 0 else 0
    
    # Base assessment by exposure level
    if exposure_level == "Low":
        base_text = "This document appears to follow standard practices with minimal concerning terms. "
        if coverage_pct >= 80:
            base_text += "Most expected protections are present. "
        else:
            base_text += f"However, only {found} of {expected} expected clause categories were found. "
    
    elif exposure_level == "Moderate":
        base_text = "This document contains some terms that warrant careful review. "
        if coverage_pct >= 70:
            base_text += "Key protections are mostly present, but "
        else:
            base_text += f"Only {found} of {expected} expected protections were found, and "
    
    elif exposure_level == "Elevated":
        base_text = "This document has notable imbalances that require attention. "
        if coverage_pct < 60:
            base_text += f"Significant gaps exist ({found}/{expected} expected clauses found), and "
        else:
            base_text += "While some protections exist, "
    
    else:  # High
        base_text = "This document contains significant one-sided terms. "
        if coverage_pct < 50:
            base_text += f"Critical protections are largely missing ({found}/{expected} found), and "
        else:
            base_text += "Despite some standard clauses, "
    
    # Add top factors
    if len(top_factors) >= 2:
        base_text += f"primary concerns include: {top_factors[0].lower()}, and {top_factors[1].lower()}. "
    elif len(top_factors) == 1:
        base_text += f"the main concern is: {top_factors[0].lower()}. "
    
    # Add document type confidence note if low
    if doc_type_confidence < 0.5:
        base_text += "Note: Document type detection had low confidence; results may be less specific."
    
    return base_text.strip()


def generate_verdict(score):
    """Generate the one-sentence takeaway (Plain English, no scores initially)"""
    if score >= 8.0:
        return {
            "label": "Generally Standard",
            "color": "green",
            "emoji": "✅",
            "text": "This document appears standard, but a few clauses may favor the provider."
        }
    elif score >= 6.0:
        return {
            "label": "Review Carefully",
            "color": "orange",
            "emoji": "⚠️",
            "text": "Most terms are standard, but some specific clauses create imbalance."
        }
    return {
        "label": "High Risk Factors",
        "color": "red",
        "emoji": "🛑",
        "text": "This document contains significant one-sided terms that require attention."
    }

def synthesize_top_risks(document, report_data, max_items=3):
    """
    Pick exactly 3 high-impact risks with context-aware explanations.
    Uses the new Humanization Layer logic.
    """
    try:
        from .insights import build_insight_context, generate_insight
        import logging
        logger = logging.getLogger(__name__)
        
        context = build_insight_context(document)
        candidates = []
        
        # Helper to safely get insight
        def get_insight_safe(pattern_key, source_label, origin_severity="MEDIUM"):
            try:
                insight = generate_insight(pattern_key, context)
                return {
                    "title": insight.get("title", pattern_key),
                    "what_is_happening": insight.get("explanation", ""), # Mapped from 'message' or 'what_is_happening'
                    "why_this_matters": insight.get("what_this_means", ""), # mapped from 'why_this_matters'
                    "how_common": insight.get("how_common", "Varies by contract type."), # New field
                    "found_in": source_label,
                    "icon": insight.get("icon", "⚠️"),
                    "severity": insight.get("severity", origin_severity),
                    # Store original keys for grouping
                    "original_pattern": pattern_key
                }
            except Exception as e:
                logger.warning(f"Failed to generate insight for {pattern_key}: {e}")
                return None

        # 1. Collect from Favorability Analysis
        fav = report_data.get("favorability", {})
        if isinstance(fav, dict):
            for u in fav.get("unfavorable_clauses", []):
                if u.get("risk_level") in ["HIGH", "MEDIUM"]:
                    label = u.get("clause_label", "").title()
                    # MAPPING: Map recognized clauses to Pattern Keys
                    pattern_map = {
                        "Indemnification": "unilateral_indemnification",
                        "Liability": "Liability",
                        "Termination": "one_sided_termination",
                        "Dispute Resolution": "Dispute Resolution",
                        "Modifications To Terms": "Modifications to Terms"
                    }
                    pattern_key = pattern_map.get(label, label)
                    c = get_insight_safe(pattern_key, f"Clause: {label}", u.get("risk_level"))
                    if c: candidates.append(c)

        # 2. Collect from Asymmetries
        for a in report_data.get("asymmetries", []):
            if isinstance(a, dict):
                asym_type = a.get("type", "")
                c = get_insight_safe(asym_type, "One-Sided Term", a.get("severity", "MEDIUM"))
                if c: candidates.append(c)

        # 3. GROUPING LOGIC (The "Signal Grouping" Layer)
        # We want to merge "Indemnification" and "Liability" risks if both exist
        grouped_candidates = []
        financial_risks = []
        
        for c in candidates:
            # Check for financial/liability keywords
            msg = (c["title"] + c["what_is_happening"]).lower()
            if "indemn" in msg or "liabil" in msg or "cost" in msg or "pay" in msg:
                 financial_risks.append(c)
            else:
                 grouped_candidates.append(c)
                 
        # If we have multiple financial risks, create a merged group
        if len(financial_risks) > 1:
            # Find the most severe one to represent the group
            primary = max(financial_risks, key=lambda x: 1 if x["severity"]=="HIGH" else 0)
            
            merged = {
                "title": "Legal Cost & Liability Exposure",
                "what_is_happening": primary["what_is_happening"] + " Also includes other liability risks.",
                "why_this_matters": "Combined, these terms significantly increase your financial exposure.",
                "how_common": "Common in provider-friendly terms, but risky.",
                "found_in": "Multiple Sections",
                "icon": "💰",
                "severity": "HIGH" 
            }
            grouped_candidates.append(merged)
        elif len(financial_risks) == 1:
            grouped_candidates.append(financial_risks[0])

        # Sort by severity
        severity_map = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}
        grouped_candidates.sort(key=lambda x: severity_map.get(str(x.get("severity", "LOW")).upper(), 0), reverse=True)

        # Retrieve unique top items
        top_risks = []
        seen = set()
        for c in grouped_candidates:
             if c["title"] not in seen and len(top_risks) < max_items:
                 seen.add(c["title"])
                 top_risks.append(c)
                 
        return top_risks

    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Critical error in synthesize_top_risks: {e}")
        return []



# =========================================================
# EXPECTED CLAUSES PER DOCUMENT TYPE
# Each document type only checks for its relevant clauses
# =========================================================
EXPECTED_CLAUSES = {
    "TERMS_CONDITIONS": [
        # Common
        "Termination", "Payment", "Liability", "Governing Law", "Indemnification",
        "Severability", "Amendment", "Assignment", "Entire Agreement",
        # T&C Specific
        "User Obligations", "Dispute Resolution", "Acceptable Use", "Account Terms",
        "Intellectual Property", "Service Availability", "User Content", "Privacy & Data",
        "Warranty Disclaimer", "Age/Eligibility", "Modifications to Terms", "Third-Party Services",
    ],
    "NDA_MUTUAL": [
        # Core NDA clauses (expected in most NDAs)
        "Definition of Confidential Information",
        "Exclusions from Confidential Information",
        "Confidentiality Obligations",
        "Purpose of Disclosure",
        "Non-Use Restriction",
        "Term of Agreement",
        "Survival of Confidentiality",
        "Return or Destruction of Information",
        "Governing Law",
        "Dispute Resolution",
        # Note: Optional clauses (Liability, Indemnification, Severability, etc.) 
        # are NOT included here - they're detected but not flagged as missing
    ],
    "NDA_ONEWAY": [
        # Core NDA clauses (same as mutual NDA)
        "Definition of Confidential Information",
        "Exclusions from Confidential Information",
        "Confidentiality Obligations",
        "Purpose of Disclosure",
        "Non-Use Restriction",
        "Term of Agreement",
        "Survival of Confidentiality",
        "Return or Destruction of Information",
        "Governing Law",
        "Dispute Resolution",
    ],
    "SERVICE_AGREEMENT": [
        # Service Agreement specific
        "Termination", "Payment", "Confidentiality", "Liability", "Governing Law",
        "Indemnification", "Force Majeure", "Severability", "Amendment", "Assignment",
        "Entire Agreement", "Dispute Resolution", "Notices",
    ],
    "PRIVACY_POLICY": [
        # Privacy Policy specific
        "Privacy & Data", "User Content", "Third-Party Services", "Termination",
        "Governing Law", "Liability", "Severability",
    ],
    "EMPLOYMENT_AGREEMENT": [
        # Employment Agreement specific
        "Termination", "Payment", "Confidentiality", "Governing Law", "Severability",
        "Assignment", "Indemnification", "Dispute Resolution", "Entire Agreement",
    ],
    "OTHER": [
        # Basic common clauses for unknown documents
        "Termination", "Payment", "Confidentiality", "Liability", "Governing Law",
        "Indemnification", "Severability",
    ],
}

# ... existing code ...


def clause_statistics(document):
    clauses = Clause.objects.filter(document=document)
    labels = [c.label for c in clauses]
    return Counter(labels)


# ... existing code ...


from .legal_bert_engine import LegalBertEngine

def risk_flags(document, purpose="Unknown"):
    stats = clause_statistics(document)
    total = sum(stats.values())
    doc_type = document.document_type

    risks = []

    # Universal checks
    
    # PURPOSE-BASED RULE: Termination Clause
    # If missing, it's only a risk if the relationship is ONGOING.
    # For Evaluation/One-time deals, missing termination is acceptable (Low Concern).
    if stats.get("Termination", 0) == 0:
        if purpose in ["Ongoing business relationship", "Employment / Service engagement"]:
            risks.append("Missing Termination Clause (Critical for Ongoing Relationship)")
        elif purpose == "Unknown" and doc_type not in ["NDA_MUTUAL", "NDA_ONEWAY", "PRIVACY_POLICY"]:
             # If we don't know the purpose, be safe and flag it, unless it's an NDA/Policy where it might be less critical or handled differently
             risks.append("Missing Termination Clause")
    
    if stats.get("Governing Law", 0) == 0:
        risks.append("Missing Governing Law")

    if total > 0:
        other_ratio = stats.get("Other", 0) / total
        if other_ratio > 0.7:
            risks.append("Low Clause Specificity")

    # Terms & Conditions specific checks
    if doc_type == "TERMS_CONDITIONS":
        if stats.get("User Obligations", 0) == 0:
            risks.append("Missing User Obligations")
        if stats.get("Dispute Resolution", 0) == 0:
            risks.append("Missing Dispute Resolution")
        if stats.get("Acceptable Use", 0) == 0:
            risks.append("Missing Acceptable Use Policy")
        if stats.get("Intellectual Property", 0) == 0:
            risks.append("Missing Intellectual Property Terms")
        if stats.get("Warranty Disclaimer", 0) == 0:
            risks.append("Missing Warranty Disclaimer")
        # Priority 1 - Essential T&C clauses
        if stats.get("Age/Eligibility", 0) == 0:
            risks.append("Missing Age/Eligibility Requirements")
        if stats.get("Modifications to Terms", 0) == 0:
            risks.append("Missing Terms Modification Clause")
        if stats.get("Third-Party Services", 0) == 0:
            risks.append("Missing Third-Party Disclaimer")
        if stats.get("Indemnification", 0) == 0:
            risks.append("Missing Indemnification Clause")

    # NDA specific checks
    elif doc_type in ["NDA_MUTUAL", "NDA_ONEWAY"]:
        if stats.get("Confidentiality", 0) == 0 and stats.get("Definition of Confidential Information", 0) == 0:
            risks.append("Missing Definition of Confidential Information")
        if stats.get("Confidentiality Obligations", 0) == 0:
            risks.append("Missing Confidentiality Obligations")
        if stats.get("Exclusions from Confidential Information", 0) == 0:
            risks.append("Missing Exclusions Clause - Critical for NDA")
        if stats.get("Non-Use Restriction", 0) == 0:
            risks.append("Missing Non-Use Restriction")
        if stats.get("Return or Destruction of Information", 0) == 0:
            risks.append("Missing Return/Destruction of Information Clause")
        if stats.get("Survival of Confidentiality", 0) == 0:
            risks.append("Missing Survival Clause - Obligations may end at termination")
        if stats.get("Purpose of Disclosure", 0) == 0:
            risks.append("Missing Purpose of Disclosure")

    # Service Agreement specific checks
    elif doc_type == "SERVICE_AGREEMENT":
        if stats.get("Payment", 0) == 0:
            risks.append("Missing Payment Terms")

    # Privacy Policy specific checks
    elif doc_type == "PRIVACY_POLICY":
        if stats.get("Privacy & Data", 0) == 0:
            risks.append("Missing Data Processing Terms")

    # Employment Agreement specific checks
    elif doc_type == "EMPLOYMENT_AGREEMENT":
        if stats.get("Payment", 0) == 0:
            risks.append("Missing Compensation Terms")

    return risks


def risk_summary(document):
    stats = clause_statistics(document)
    total = sum(stats.values())
    doc_type = document.document_type
    
    # 1. Detect Purpose using Legal-BERT
    # Extract first ~2000 chars for intro analysis
    intro_text = document.extracted_text[:2000] if document.extracted_text else ""
    try:
        engine = LegalBertEngine.get_instance()
        purpose, confidence = engine.detect_purpose(intro_text)
    except Exception as e:
        purpose = "Unknown"
        confidence = 0.0
        # logger.error(f"Purpose detection failed: {e}") # Ensure logger is available or skip

    # Get expected clauses for THIS document type only (not ALL clauses)
    expected_labels = EXPECTED_CLAUSES.get(doc_type, EXPECTED_CLAUSES["OTHER"])

    good = []
    missing = []

    for label in expected_labels:
        count = stats.get(label, 0)
        if count > 0:
            good.append({"label": label, "count": count})
        else:
            missing.append(label)

    risks = risk_flags(document, purpose=purpose)
    
    # NEW: Categorize missing clauses by importance to reduce user anxiety
    categorized_missing = categorize_missing_clauses(doc_type, missing)

    return {
        "document_id": document.id,
        "title": document.title,
        "total_clauses": total,
        "purpose": purpose, # Return the detected purpose
        "purpose_confidence": confidence,
        "by_label": dict(stats),
        "good": good,
        "missing": missing,  # Keep for backward compatibility
        "missing_critical": categorized_missing["critical"],  # NEW: Critical missing clauses
        "missing_important": categorized_missing["important"],  # NEW: Important missing clauses
        "missing_optional": categorized_missing["optional"],  # NEW: Optional missing clauses
        "risks": risks,
    }


def _generate_summary_text(document, summary_data):
    doc_type = document.get_document_type_display()
    total = summary_data["total_clauses"]
    good = summary_data["good"]
    missing = summary_data["missing"]
    risks = summary_data["risks"]
    purpose = summary_data.get("purpose", "Unknown")

    parts = []

    if doc_type and doc_type != "Other/Unknown":
        parts.append(f"This looks like a {doc_type}.")
    else:
        parts.append("This document type could not be confidently identified.")
        
    if purpose != "Unknown":
        parts.append(f"Based on the detected purpose ({purpose}), the system has tried to contextualize missing clauses.")

    if total > 0:
        parts.append(f"It contains {total} clauses in total.")
    else:
        parts.append("No clauses were extracted from this document.")

    if good:
        labels = ", ".join(item["label"] for item in good)
        parts.append(f"The following key clause types are present: {labels}.")

    if missing:
        missing_labels = ", ".join(missing)
        parts.append(
            f"The system did not detect some expected clause types: {missing_labels}."
        )

    if risks:
        risk_text = "; ".join(risks)
        parts.append(f"Potential issues flagged: {risk_text}.")
    else:
        parts.append("No major risks were flagged by the rule-based analysis.")

    return " ".join(parts)

# Report caching version - increment when analysis logic changes
RULES_VERSION = "v1.2.0"

def build_document_report(document, document_type_override=None):
    """
    Build a combined report for a document:
    - document metadata
    - stats (total + by_label)
    - risk summary
    - key clause highlights
    - plain-text summary
    
    CACHING: Reports are cached in the database to avoid recomputation.
    Cache is invalidated when:
    - Document text changes (tracked via updated_at)
    - RULES_VERSION changes
    - document_type_override is provided (bypasses cache)
    """
    import hashlib
    from django.utils import timezone
    
    # If override is provided, skip cache and use override type
    if document_type_override:
        # Bypass cache when override is used
        summary_data = risk_summary(document)
        doc_type = document_type_override
    else:
        # Generate cache key based on document state and rules version
        cache_key_data = f"{document.id}:{document.uploaded_at.isoformat()}:{RULES_VERSION}"
        cache_key = hashlib.sha256(cache_key_data.encode()).hexdigest()
        
        # Check if we have a valid cached report
        if (document.report_cache and 
            document.report_cache_key == cache_key and 
            document.report_cached_at):
            # Cache hit - return cached report
            return document.report_cache
        
        # Cache miss - compute report
        summary_data = risk_summary(document)
        doc_type = document.document_type

    # Document-type-specific important clauses
    if doc_type == "TERMS_CONDITIONS":
        important_labels = [
            "User Obligations",
            "Liability",
            "Indemnification",
            "Dispute Resolution",
            "Acceptable Use",
            "Age/Eligibility",
            "Intellectual Property",
            "Modifications to Terms",
            "Third-Party Services",
            "Termination",
            "Warranty Disclaimer",
            "Governing Law",
            "Severability",
        ]
    elif doc_type in ["NDA_MUTUAL", "NDA_ONEWAY"]:
        important_labels = [
            # Core NDA clauses (matching EXPECTED_CLAUSES - only 10 core clauses)
            "Definition of Confidential Information",
            "Exclusions from Confidential Information",
            "Confidentiality Obligations",
            "Purpose of Disclosure",
            "Non-Use Restriction",
            "Term of Agreement",
            "Survival of Confidentiality",
            "Return or Destruction of Information",
            "Governing Law",
            "Dispute Resolution",
            # Optional clauses - shown if present but not flagged if missing
            "Permitted Disclosures",
            "Remedies for Breach",
            "Liability",
            "Indemnification",
            "Ownership of Information",
            "Termination",
            "No Waiver",
            "Severability",
            "Entire Agreement",
            "Amendment",
            "Assignment",
        ]
    elif doc_type == "SERVICE_AGREEMENT":
        important_labels = [
            "Payment",
            "Termination",
            "Liability",
            "Indemnification",
            "Confidentiality",
            "Force Majeure",
            "Governing Law",
            "Severability",
        ]
    elif doc_type == "PRIVACY_POLICY":
        important_labels = [
            "Privacy & Data",
            "User Content",
            "Third-Party Services",
            "Termination",
            "Governing Law",
        ]
    elif doc_type == "EMPLOYMENT_AGREEMENT":
        important_labels = [
            "Payment",
            "Termination",
            "Confidentiality",
            "Governing Law",
            "Severability",
            "Assignment",
        ]
    else:
        important_labels = [
            "Termination",
            "Liability",
            "Indemnification",
            "Governing Law",
            "Confidentiality",
            "Payment",
            "Severability",
        ]

    key_clauses = []
    for label in important_labels:
        clause = (
            Clause.objects.filter(document=document, label=label)
            .order_by("id")
            .first()
        )
        if clause:
            key_clauses.append(
                {
                    "label": label,
                    "id": clause.id,
                    "text": clause.text,
                }
            )

    summary_text = _generate_summary_text(document, summary_data)

    # Detect loopholes
    loopholes_data = detect_loopholes(document)
    
    # ENHANCEMENT: Add favorability analysis
    favorability_summary = generate_favorability_summary(document)
    
    # ENHANCEMENT: Detect asymmetries
    asymmetries = detect_asymmetry(document)

    # Build the base report
    report = {
        "document": {
            "id": document.id,
            "title": document.title,
            "document_type": document.document_type,
            "document_type_display": document.get_document_type_display(),
            "detected_type_confidence": getattr(
                document, "detected_type_confidence", 0.0
            ),
            "uploaded_at": document.uploaded_at,
        },
        "stats": {
            "total_clauses": summary_data["total_clauses"],
            "by_label": summary_data["by_label"],
        },
        "risk_summary": {
            "good": summary_data["good"],
            "missing": summary_data["missing"],
            "risks": summary_data["risks"],
            "missing_critical": summary_data.get("missing_critical", []),
            "missing_important": summary_data.get("missing_important", []),
            "missing_optional": summary_data.get("missing_optional", []),
        },
        "highlights": {
            "key_clauses": key_clauses,
        },
        "summary_text": summary_text,
        "loopholes": loopholes_data,
        "favorability": favorability_summary,
        "asymmetries": asymmetries,
    }

    # =========================================================
    # INVERTED PYRAMID: Add scoring, verdict, and top risks
    # =========================================================
    score = calculate_safety_score(summary_data, favorability_summary, asymmetries, loopholes_data)
    report["safety_score"] = score
    report["verdict"] = generate_verdict(score)
    report["top_risks"] = synthesize_top_risks(document, report, max_items=3)
    
    # =========================================================
    # UI OPTION A: Exposure Level + Top Factors + Coverage
    # =========================================================
    exposure_level = get_exposure_level(score)
    top_factors = generate_top_factors(summary_data, favorability_summary, asymmetries, loopholes_data)
    
    # Calculate clause coverage
    expected_labels = EXPECTED_CLAUSES.get(doc_type, EXPECTED_CLAUSES["OTHER"])
    found_labels = {item["label"] for item in summary_data["good"]}
    clause_coverage = {
        "found": len(found_labels),
        "expected": len(expected_labels)
    }
    
    # Generate overall assessment text (deterministic, no LLM)
    doc_type_confidence = getattr(document, "detected_type_confidence", 1.0)
    overall_assessment_text = generate_overall_assessment(
        exposure_level, 
        top_factors, 
        clause_coverage, 
        doc_type_confidence
    )
    
    # Add to report
    report["exposure_level"] = exposure_level
    report["top_factors"] = top_factors
    report["clause_coverage"] = clause_coverage
    report["overall_assessment_text"] = overall_assessment_text

    # =========================================================
    # FINANCIAL & EXPIRATION ANALYSIS
    # =========================================================
    from .financial_utils import extract_expiration_info, extract_penalties, extract_all_financial_data
    
    # 0. Full Financial Data (New Structured Format)
    report["financial_data"] = extract_all_financial_data(document.extracted_text)

    # 1. Expiration

    expiration_info = extract_expiration_info(document.extracted_text)
    if expiration_info["found"]:
        date_str = expiration_info.get("date", "specified date")
        if date_str == "See source":
             expiration_info["explanation"] = "Expiration language was detected, but a specific date could not be parsed. Please check the clause text."
        else:
             expiration_info["explanation"] = f"This text indicates the agreement is valid until {date_str}. After this, obligations may cease unless renewed."
    else:
        expiration_info["explanation"] = "No explicit expiration date detected. The agreement may be perpetual or terminate upon completion of services."
    
    report["expiration"] = expiration_info

    # 2. Penalties
    penalties_data = extract_penalties(
        document.extracted_text, 
        doc_type=document.document_type,
        purpose=summary_data.get("purpose", "Unknown")
    )
    # Add explanations
    for p in penalties_data:
        amount_disp = p.get("amount", "an unspecified amount")
        p["explanation"] = f"A penalty of {amount_disp} may apply. Please review the source clause for specific conditions."

    report["penalties"] = penalties_data

    # =========================================================
    # CACHE THE REPORT
    # =========================================================
    from django.utils import timezone
    from datetime import datetime, date
    
    def make_json_serializable(obj):
        """
        Recursively convert datetime objects to ISO strings for JSONField compatibility.
        Django's JSONField uses json.dumps() which cannot serialize datetime objects.
        """
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        elif isinstance(obj, dict):
            return {key: make_json_serializable(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [make_json_serializable(item) for item in obj]
        else:
            return obj
    
    # Convert report to JSON-serializable format for caching
    # (original report object remains unchanged for API response)
    # Only cache if no override was used
    if not document_type_override:
        serializable_report = make_json_serializable(report)
        document.report_cache = serializable_report
        document.report_cached_at = timezone.now()
        document.report_cache_key = cache_key
        document.save(update_fields=['report_cache', 'report_cached_at', 'report_cache_key'])

    return report