import re
from .models import Clause

# Loophole detection patterns with severity and reasoning
LOOPHOLE_PATTERNS = {
    "vague_language": {
        "patterns": [
            (r"\breasonable\s+(time|period|notice|efforts?|care)\b", "reasonable [term]"),
            (r"\bpromptly\b", "promptly"),
            (r"\bbest\s+efforts?\b", "best efforts"),
            (r"\bcommercially\s+reasonable\b", "commercially reasonable"),
            (r"\bas\s+soon\s+as\s+possible\b", "as soon as possible"),
            (r"\bin\s+a\s+timely\s+manner\b", "in a timely manner"),
            (r"\bappropriate\b", "appropriate"),
            (r"\badequate\b", "adequate"),
            (r"\bsubstantial\b", "substantial"),
            (r"\bmaterial\b(?!\s+breach)", "material"),
        ],
        "severity": "MEDIUM",
        "category": "Vague Language",
        "reasoning": "Vague or subjective terms lack clear, measurable criteria and can lead to disputes over interpretation and compliance.",
    },
    "unlimited_liability": {
        "patterns": [
            (r"\bliable\s+for\s+all\s+(damages?|losses?)\b", "liable for all damages/losses"),
            (r"\bunlimited\s+liability\b", "unlimited liability"),
            (r"\bwithout\s+limit(ation)?\b", "without limitation"),
            (r"\ball\s+damages?\s+whatsoever\b", "all damages whatsoever"),
        ],
        "severity": "CRITICAL",
        "category": "Unlimited Liability Exposure",
        "reasoning": "Unlimited liability exposes a party to unbounded financial risk. Industry best practice is to cap liability at a reasonable multiple of contract value.",
    },
    "one_sided_termination": {
        "patterns": [
            (r"\bonly\s+\w+\s+may\s+terminate\b", "only [party] may terminate"),
            (r"\b\w+\s+reserves?\s+the\s+right\s+to\s+terminate\b", "[party] reserves right to terminate"),
            (r"\bat\s+\w+\'?s?\s+sole\s+discretion.*terminate\b", "at [party]'s sole discretion...terminate"),
        ],
        "severity": "HIGH",
        "category": "One-Sided Termination Rights",
        "reasoning": "When only one party can terminate, it creates a power imbalance. Fair agreements typically allow mutual termination rights.",
    },
    "weak_ip_rights": {
        "patterns": [
            (r"\bmay\s+own\b.*\b(intellectual\s+property|work\s+product|deliverables?)\b", "may own [IP/work product]"),
            (r"\bmight\s+be\s+owned\b", "might be owned"),
            (r"\b(work\s+product|deliverables?|intellectual\s+property).*\bmay\s+be\b", "[IP] may be"),
        ],
        "severity": "HIGH",
        "category": "Ambiguous IP Ownership",
        "reasoning": "Using 'may' or 'might' creates uncertainty about intellectual property ownership, which can lead to costly disputes. IP ownership should be clearly and definitively stated.",
    },
    "no_liability_cap": {
        "patterns": [
            (r"\bindemnif(y|ication)\b(?!.*\blimit)", "indemnify without limit"),
        ],
        "severity": "HIGH",
        "category": "Missing Liability Cap",
        "reasoning": "Indemnification clauses without liability caps can expose a party to excessive financial risk beyond the contract value.",
    },
    "automatic_renewal": {
        "patterns": [
            (r"\bautomatically\s+renew(s|ed|al)?\b", "automatically renews"),
            (r"\bauto-renew(s|ed|al)?\b", "auto-renewal"),
        ],
        "severity": "MEDIUM",
        "category": "Automatic Renewal Trap",
        "reasoning": "Automatic renewal clauses can lock parties into unwanted extensions. Clear notice requirements and opt-out procedures should be specified.",
    },
    "broad_warranty_disclaimer": {
        "patterns": [
            (r"\bno\s+warrant(y|ies)\b.*\bwhatsoever\b", "no warranties whatsoever"),
            (r"\bas\s+is\b.*\bno\s+warrant(y|ies)\b", "as is, no warranties"),
            (r"\bdisclaims?\s+all\s+warrant(y|ies)\b", "disclaims all warranties"),
        ],
        "severity": "HIGH",
        "category": "Broad Warranty Disclaimer",
        "reasoning": "Sweeping warranty disclaimers may leave one party without recourse if the product/service is defective or unsuitable.",
    },
}

# Missing clause checks
# Global checks applicable to all documents
GLOBAL_MISSING_CHECKS = {
    "force_majeure": {
        "keywords": [r"\bforce\s+majeure\b", r"\bact\s+of\s+god\b", r"\bunforeseeable\s+circumstances\b"],
        "severity": "MEDIUM",
        "category": "Missing Force Majeure Clause",
        "reasoning": "Without a force majeure clause, parties may be held liable for non-performance due to uncontrollable events like natural disasters or pandemics.",
        "suggestion": "Add a force majeure clause that excuses performance during events beyond reasonable control.",
    },
    "dispute_resolution": {
        "keywords": [r"\barbitration\b", r"\bmediation\b", r"\bdispute\s+resolution\b", r"\bconflict\s+resolution\b", r"\bjurisdiction\b"],
        "severity": "MEDIUM",
        "category": "Missing Dispute Resolution Mechanism",
        "reasoning": "Without a defined dispute resolution process, parties may face costly and time-consuming litigation.",
        "suggestion": "Add a dispute resolution clause specifying mediation, arbitration, or exclusive jurisdiction.",
    },
}

# Type-specific checks
TYPE_SPECIFIC_MISSING_CHECKS = {
    "NDA_MUTUAL": {
        "permitted_disclosure": {
            "keywords": [r"\bpermitted\s+disclosure\b", r"\bneed\s+to\s+know\b", r"\bauthorized\s+representatives?\b"],
            "severity": "HIGH",
            "category": "Missing Permitted Disclosure",
            "reasoning": "NDAs should clearly state who can receive confidential information (e.g., employees, legal counsel, accountants) without breaching the agreement.",
            "suggestion": "Add a clause explicitly allowing disclosure to employees, potential investors, and legal/financial advisors on a need-to-know basis.",
        },
        "return_of_info": {
            "keywords": [r"\breturn\s+(of|or)\s+destruction\b", r"\breturn\s+confidential\s+information\b", r"\bdestroy\s+confidential\s+information\b"],
            "severity": "MEDIUM",
            "category": "Missing Return/Destruction Clause",
            "reasoning": "The agreement should specify that confidential information must be returned or destroyed upon termination to prevent indefinite retention.",
            "suggestion": "Include a clause requiring the return or destruction of all confidential materials upon termination or request.",
        },
        "exclusions": {
            "keywords": [r"\bexclusions?\b", r"\bpublicly\s+available\b", r"\bindependently\s+developed\b", r"\bpublic\s+domain\b"],
            "severity": "CRITICAL",
            "category": "Missing Standard Exclusions",
            "reasoning": "Standard exclusions (e.g., info already public or independently developed) are crucial to prevent overly broad confidentiality obligations.",
            "suggestion": "Add standard exclusions for information that is public, already known, or independently developed.",
        }
    },
    "NDA_ONEWAY": {
        "permitted_disclosure": {
            "keywords": [r"\bpermitted\s+disclosure\b", r"\bneed\s+to\s+know\b"],
            "severity": "HIGH",
            "category": "Missing Permitted Disclosure",
            "reasoning": "Even unilateral NDAs should allow the recipient to share information with necessary employees or advisors.",
            "suggestion": "Allow disclosure to employees and professional advisors who need to know the information.",
        },
        "exclusions": {
            "keywords": [r"\bexclusions?\b", r"\bpublicly\s+available\b", r"\bpublic\s+domain\b"],
            "severity": "CRITICAL",
            "category": "Missing Standard Exclusions",
            "reasoning": "Without standard exclusions, the recipient could be liable for disclosing information that is already public.",
            "suggestion": "Ensure standard exclusions (public domain, prior knowledge) are included to protect the recipient.",
        }
    },
    "EMPLOYMENT_AGREEMENT": {
        "ip_assignment": {
            "keywords": [r"\bip\s+assignment\b", r"\bwork\s+made\s+for\s+hire\b", r"\binvention\s+assignment\b", r"\bownership\s+of\s+work\b"],
            "severity": "HIGH",
            "category": "Missing IP/Invention Assignment",
            "reasoning": "Employers need clear ownership of work created by employees. Missing this clause can lead to disputes over IP ownership.",
            "suggestion": "Add an IP assignment clause stating all work created during employment belongs to the employer.",
        },
        "termination_notice": {
            "keywords": [r"\bnotice\s+period\b", r"\btermination\s+for\s+cause\b", r"\bseverance\b"],
            "severity": "MEDIUM",
            "category": "Missing Notice Period/Severance",
            "reasoning": "Clear termination procedures and notice periods protect both parties from abrupt dismissal without compensation.",
            "suggestion": "Define specific notice periods for termination (e.g., 2 weeks, 30 days) and any severance conditions.",
        },
        "confidentiality": {
            "keywords": [r"\bconfidentiality\b", r"\bnon[- ]?disclosure\b"],
            "severity": "HIGH",
            "category": "Missing Confidentiality Obligations",
            "reasoning": "Employees often handle sensitive data. A confidentiality clause is essential to protect company trade secrets.",
            "suggestion": "Include strict confidentiality obligations regarding company data and trade secrets.",
        }
    },
    "SERVICE_AGREEMENT": { # SaaS / Service
        "sla": {
            "keywords": [r"\bservice\s+level\b", r"\bsla\b", r"\buptime\b", r"\bavailability\b", r"\brefund\b"],
            "severity": "MEDIUM",
            "category": "Missing Service Level Agreement (SLA)",
            "reasoning": "For service providers, an SLA defines expected performance (uptime, support response). Missing it leaves quality standards ambiguous.",
            "suggestion": "Include an SLA defining uptime guarantees, support response times, and remedies for downtime.",
        },
        "data_security": {
            "keywords": [r"\bdata\s+security\b", r"\bsecurity\s+measures\b", r"\bbreach\s+notification\b", r"\bencryption\b"],
            "severity": "HIGH",
            "category": "Missing Data Security/Privacy",
            "reasoning": "Agreements involving data handling must specify security measures and breach notification procedures.",
            "suggestion": "Add data security clauses specifying encryption standards and breach notification timelines.",
        },
        "limitation_liability": {
            "keywords": [r"\blimitation\s+of\s+liability\b", r"\bcap\s+on\s+liability\b", r"\bmaximum\s+liability\b"],
            "severity": "CRITICAL",
            "category": "Missing Limitation of Liability",
            "reasoning": "Service providers must limit their liability to avoid catastrophic risk from lawsuits.",
            "suggestion": "Add a limitation of liability clause capping damages (e.g., to 12 months' fees).",
        }
    },
    "PRIVACY_POLICY": {
        "cookies": {
            "keywords": [r"\bcookies?\b", r"\btracking\s+technologies\b"],
            "severity": "MEDIUM",
            "category": "Missing Cookie Policy",
            "reasoning": "Privacy laws require disclosure of cookie usage and tracking technologies.",
            "suggestion": "Should describe the use of cookies and how users can manage them.",
        },
        "user_rights": {
            "keywords": [r"\buser\s+rights\b", r"\bdata\s+subject\s+rights\b", r"\baccess\b", r"\bdeletion\b", r"\bopt[- ]?out\b"],
            "severity": "HIGH",
            "category": "Missing User Rights (GDPR/CCPA)",
            "reasoning": "Modern privacy laws (GDPR, CCPA) require explicitly stating user rights to access, delete, or opt-out of data collection.",
            "suggestion": "Explicitly list user rights regarding their data (access, correction, deletion).",
        }
    }
}


def _check_clause_for_patterns(clause, pattern_category):
    """Check a single clause against a pattern category."""
    findings = []
    config = LOOPHOLE_PATTERNS[pattern_category]
    text_lower = clause.text.lower()
    
    for pattern, match_label in config["patterns"]:
        matches = re.finditer(pattern, text_lower, re.IGNORECASE)
        for match in matches:
            # FILTER: Ignore "includes without limitation" false positives (definitional usage)
            if match_label == "without limitation":
                pre_context = text_lower[max(0, match.start() - 35):match.start()]
                # Check if preceded by "include", "includes", "including"
                if re.search(r"\binclud(e|es|ing)\b", pre_context):
                    continue

            # Extract context around the match (40 chars before and after)
            start = max(0, match.start() - 40)
            end = min(len(clause.text), match.end() + 40)
            context = clause.text[start:end].strip()
            
            findings.append({
                "severity": config["severity"],
                "category": config["category"],
                "clause_id": clause.id,
                "clause_text": clause.text[:200],  # First 200 chars
                "matched_text": match.group(0),
                "context": context,
                "issue": f"Contains undefined/vague term: '{match_label}'",
                "reasoning": config["reasoning"],
                "risk_impact": _get_risk_impact(config["severity"]),
                "suggestion": _get_suggestion_for_pattern(pattern_category, match_label),
            })
    
    return findings


def _check_missing_clauses(document):
    """Check for missing important clauses based on document context."""
    findings = []
    all_text = document.extracted_text.lower()
    
    # 1. Determine which checks to run
    # Start with global checks
    checks_to_run = GLOBAL_MISSING_CHECKS.copy()
    
    # Add document-type specific checks
    doc_type = getattr(document, "document_type", "OTHER")
    if doc_type in TYPE_SPECIFIC_MISSING_CHECKS:
        checks_to_run.update(TYPE_SPECIFIC_MISSING_CHECKS[doc_type])
    
    # Also verify based on detected Clause objects if possible (hybrid approach)
    all_clauses = Clause.objects.filter(document=document)
    
    for check_id, check_config in checks_to_run.items():
        # Check if any keywords are present in the full text
        # This is a broad "does the concept exist?" check
        has_concept = any(
            re.search(keyword, all_text, re.IGNORECASE)
            for keyword in check_config["keywords"]
        )
        
        # Refinement: If specific labels are required, verify those Clause objects exist
        # This prevents false positives where a keyword matches but the actual clause is missing
        if "labels" in check_config and has_concept:
            has_relevant_clauses = all_clauses.filter(
                label__in=check_config["labels"]
            ).exists()
            if not has_relevant_clauses:
                # Concept text exists but wasn't classified as the expected label
                # This indicates weak/missing core clause - override has_concept
                has_concept = False 
                
        if not has_concept:
            findings.append({
                "severity": check_config["severity"],
                "category": check_config["category"],
                "clause_id": None,
                "clause_text": None,
                "matched_text": None,
                "context": None,
                "issue": f"{check_config['category']}",
                "reasoning": check_config["reasoning"],
                "risk_impact": _get_risk_impact(check_config["severity"]),
                "suggestion": check_config["suggestion"],
            })
    
    return findings


def _get_risk_impact(severity):
    """Get human-readable risk impact based on severity."""
    impact_map = {
        "CRITICAL": "Extremely high risk - could result in severe financial or legal consequences",
        "HIGH": "High risk - significant potential for disputes, financial loss, or unfavorable outcomes",
        "MEDIUM": "Moderate risk - may lead to disagreements or compliance difficulties",
        "LOW": "Low risk - minor concern but worth addressing for clarity",
    }
    return impact_map.get(severity, "Unknown risk level")


def _get_suggestion_for_pattern(pattern_category, match_label):
    """Get specific suggestions for fixing detected loopholes."""
    suggestions = {
        "vague_language": f"Replace '{match_label}' with specific, measurable criteria (e.g., '5 business days', '30 calendar days', 'within 48 hours').",
        "unlimited_liability": "Add a liability cap clause limiting total liability to a reasonable amount (e.g., '2x the total fees paid under this agreement').",
        "one_sided_termination": "Modify to allow mutual termination rights with equal notice periods, or clearly justify why asymmetric rights are necessary.",
        "weak_ip_rights": "Replace 'may' or 'might' with definitive language like 'shall own' or 'is the exclusive owner of' to clearly establish IP ownership.",
        "no_liability_cap": "Add an explicit cap on indemnification liability to limit financial exposure.",
        "automatic_renewal": "Add clear opt-out provisions with specific notice requirements (e.g., '60 days written notice before renewal date').",
        "broad_warranty_disclaimer": "Balance the disclaimer with some basic warranties (e.g., 'services will be performed in a professional manner consistent with industry standards').",
    }
    return suggestions.get(pattern_category, "Review and clarify this clause with legal counsel.")


def detect_loopholes(document):
    """
    Main function to analyze document for risks, ambiguity, and structural issues.
    
    Returns a dictionary with structured insights:
    - risk_indicators: Specific high-risk clauses (Unlimited Liability, One-Sided Termination)
    - ambiguous_language: Vague or undefined text (e.g., "promptly", "reasonable efforts")
    - structural_observations: Missing expected clauses contextually
    - total_count: Total issues found across all categories
    """
    all_findings = []
    clauses = Clause.objects.filter(document=document)
    
    # 1. Collect all pattern-based findings
    for clause in clauses:
        for pattern_category in LOOPHOLE_PATTERNS.keys():
            findings = _check_clause_for_patterns(clause, pattern_category)
            all_findings.extend(findings)
    
    # 2. Collect missing clause findings
    missing_findings = _check_missing_clauses(document)
    
    # 3. Deduplicate (same clause + category)
    unique_pattern_findings = []
    seen = set()
    for finding in all_findings:
        # Use clause_id and category as unique key
        key = (finding["clause_id"], finding["category"])
        if key not in seen:
            seen.add(key)
            unique_pattern_findings.append(finding)

    # 4. Group into the 3 requested categories
    risk_indicators = []
    ambiguous_language = []
    structural_observations = []

    # Process Pattern Findings
    for finding in unique_pattern_findings:
        # Check internal category/reasoning to classify
        cat_key = next((k for k, v in LOOPHOLE_PATTERNS.items() if v["category"] == finding["category"]), None)
        
        if cat_key == "vague_language":
            # Section 2: Ambiguous Language
            # Ensure "Why this matters" format
            finding["why_this_matters"] = finding["reasoning"] 
            ambiguous_language.append(finding)
        else:
            # Section 1: Risk Indicators (Primary)
            # Default to critical/high risk specific items
            finding["why_this_matters"] = finding["reasoning"]
            risk_indicators.append(finding)

    # Process Missing Findings -> Section 3: Structural Observations
    for finding in missing_findings:
        finding["why_this_matters"] = finding["reasoning"]
        structural_observations.append(finding)
    
    # Sort within categories
    # Risk Indicators: Critical > High > Medium
    severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    risk_indicators.sort(key=lambda x: severity_order.get(x["severity"], 4))
    
    # Total count for stats
    total_count = len(risk_indicators) + len(ambiguous_language) + len(structural_observations)

    return {
        "risk_indicators": risk_indicators,
        "ambiguous_language": ambiguous_language,
        "structural_observations": structural_observations,
        "total_count": total_count,
        # Keep legacy list for backward compatibility if needed, but the UI should switch
        "loopholes": risk_indicators + ambiguous_language + structural_observations 
    }
