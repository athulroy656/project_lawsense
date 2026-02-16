"""
Document-type-specific clause importance levels
Helps users understand which missing clauses are critical vs. optional
"""

# Define importance levels for each document type
CLAUSE_IMPORTANCE = {
    "TERMS_CONDITIONS": {
        # CRITICAL - Should almost always be present
        "HIGH": [
            "User Obligations",
            "Dispute Resolution", 
            "Warranty Disclaimer",
            "Modifications to Terms",
            "Indemnification",
        ],
        # IMPORTANT - Good to have for completeness
        "MEDIUM": [
            "Acceptable Use",
            "Age/Eligibility",
            "Third-Party Services",
            "Intellectual Property",
            "Privacy & Data",
            "Service Availability",
            "User Content",
        ],
        # OPTIONAL - Nice to have but not critical
        "LOW": [
            "Payment",  # Not all T&C have payment
            "Termination",  # Sometimes implicit
            "Liability",
            "Governing Law",
            "Severability",
            "Amendment",
            "Assignment",
            "Entire Agreement",
            "Account Terms",
        ],
    },
    "NDA_MUTUAL": {
        "HIGH": [
            "Definition of Confidential Information",
            "Confidentiality Obligations",
            "Exclusions from Confidential Information",
            "Non-Use Restriction",
            "Return or Destruction of Information",
        ],
        "MEDIUM": [
            "Purpose of Disclosure",
            "Term of Agreement",
            "Survival of Confidentiality",
            "Governing Law",
            "Dispute Resolution",
        ],
        "LOW": [
            "Permitted Disclosures",
            "Remedies for Breach",
            "No Waiver",
            "Counterparts",
            "Severability",
        ],
    },
    "NDA_ONEWAY": {
        "HIGH": [
            "Definition of Confidential Information",
            "Confidentiality Obligations",
            "Exclusions from Confidential Information",
            "Non-Use Restriction",
            "Return or Destruction of Information",
        ],
        "MEDIUM": [
            "Purpose of Disclosure",
            "Term of Agreement",
            "Survival of Confidentiality",
            "Governing Law",
        ],
        "LOW": [
            "Permitted Disclosures",
            "Remedies for Breach",
            "Severability",
        ],
    },
    "SERVICE_AGREEMENT": {
        "HIGH": [
            "Payment",
            "Termination",
            "Liability",
            "Indemnification",
        ],
        "MEDIUM": [
            "Confidentiality",
            "Governing Law",
            "Dispute Resolution",
            "Force Majeure",
        ],
        "LOW": [
            "Severability",
            "Amendment",
            "Assignment",
            "Entire Agreement",
            "Notices",
        ],
    },
    "PRIVACY_POLICY": {
        "HIGH": [
            "Privacy & Data",
            "User Content",
        ],
        "MEDIUM": [
            "Third-Party Services",
            "Governing Law",
        ],
        "LOW": [
            "Termination",
            "Liability",
            "Severability",
        ],
    },
    "EMPLOYMENT_AGREEMENT": {
        "HIGH": [
            "Payment",
            "Termination",
            "Confidentiality",
        ],
        "MEDIUM": [
            "Governing Law",
            "Dispute Resolution",
            "Indemnification",
        ],
        "LOW": [
            "Severability",
            "Assignment",
            "Entire Agreement",
        ],
    },
    "OTHER": {
        "HIGH": [
            "Termination",
            "Liability",
        ],
        "MEDIUM": [
            "Governing Law",
            "Indemnification",
        ],
        "LOW": [
            "Payment",
            "Confidentiality",
            "Severability",
        ],
    },
}

def get_clause_importance(document_type, clause_label):
    """
    Get importance level for a specific clause in a document type
    Returns: 'HIGH', 'MEDIUM', 'LOW', or 'UNKNOWN'
    """
    type_importance = CLAUSE_IMPORTANCE.get(document_type, {})
    
    if clause_label in type_importance.get("HIGH", []):
        return "HIGH"
    elif clause_label in type_importance.get("MEDIUM", []):
        return "MEDIUM"
    elif clause_label in type_importance.get("LOW", []):
        return "LOW"
    else:
        return "UNKNOWN"

def categorize_missing_clauses(document_type, missing_clauses):
    """
    Split missing clauses by importance level for better UX
    Returns: dict with 'critical', 'important', 'optional' lists
    """
    critical = []
    important = []
    optional = []
    
    for clause in missing_clauses:
        importance = get_clause_importance(document_type, clause)
        
        if importance == "HIGH":
            critical.append(clause)
        elif importance == "MEDIUM":
            important.append(clause)
        else:  # LOW or UNKNOWN
            optional.append(clause)
    
    return {
        "critical": critical,
        "important": important,
        "optional": optional,
    }
