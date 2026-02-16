
"""
Insight Generation Module

Separates pattern detection from interpretation.
Uses a Context-Aware Insight Context to generate tailored explanations.
"""
from .legal_bert_engine import LegalBertEngine
import logging

logger = logging.getLogger(__name__)

# =========================================================
# 1. INSIGHT TEMPLATES
# Structure: Pattern -> Document Type -> Purpose -> Insight
# =========================================================

INSIGHT_TEMPLATES = {
    # --- ASYMMETRY PATTERNS ---
    "unilateral_indemnification": {
        "NDA_MUTUAL": {
            "Evaluation": {
                "severity": "LOW",
                "title": "One-Way Indemnity",
                "what_is_happening": "You must pay their legal costs if they get sued because of you, but they don't have to do the same for you.",
                "why_this_matters": "In a mutual NDA, protections should usually be reciprocal. You're taking on extra risk.",
                "how_common": "Uncommon in mutual NDAs. Acceptable for quick evaluations, but push back for long-term deals."
            },
            "Ongoing": {
                "severity": "HIGH",
                "title": "Unreciprocated Liability",
                "what_is_happening": "You are acting as their insurer. You cover their risks; they do not cover yours.",
                "why_this_matters": "This exposes you to significant financial risk without any protection in return.",
                "how_common": "Unusual and risky for ongoing mutual partnerships."
            }
        },
        "TERMS_CONDITIONS": {
            "Consumer": {
                "severity": "MEDIUM",
                "title": "User-Only Indemnification",
                "what_is_happening": "You agree to cover the company's legal bills if your usage causes them a lawsuit.",
                "why_this_matters": "If you misuse the app and they get sued, you foot the bill. They offer you no similar protection.",
                "how_common": "Standard for free consumer apps. Be careful if using for business."
            }
        },
        "DEFAULT": {
            "severity": "HIGH",
            "title": "One-Sided Indemnification",
            "what_is_happening": "You protect them from legal costs; they do not protect you.",
            "why_this_matters": "Creates a financial imbalance where you bear the risk for third-party claims.",
            "how_common": "Common in provider-friendly terms, but negotiable in B2B."
        }
    },

    "one_sided_termination": {
        "SERVICE_AGREEMENT": {
            "Ongoing": {
                "severity": "HIGH",
                "title": "They Can Fire You Anytime",
                "what_is_happening": "The client can end the contract at will, but you are locked in.",
                "why_this_matters": "You cannot leave if the relationship sours, but they can cut you loose instantly.",
                "how_common": "Risky. Fair contracts usually allow both sides to terminate with notice."
            }
        },
        "TERMS_CONDITIONS": {
            "Consumer": {
                "severity": "LOW",
                "title": "Provider Termination Rights",
                "what_is_happening": "They can ban your account at any time for any reason.",
                "why_this_matters": "You could lose access to your data or audience overnight without recourse.",
                "how_common": "Standard for almost all online platforms (Facebook, YouTube, etc.)."
            }
        },
        "DEFAULT": {
            "severity": "MEDIUM",
            "title": "Unequal Termination",
            "what_is_happening": "They have easier exit rights than you do.",
            "why_this_matters": "Limits your flexibility while giving them maximum freedom.",
            "how_common": "Common in standardized vendor contracts."
        }
    },
    
    # --- GENERAL RISK PATTERNS ---
    "Modifications to Terms": {
        "TERMS_CONDITIONS": {
            "Consumer": {
                "severity": "LOW",
                "title": "Terms Can Change",
                "what_is_happening": "The provider can update these rules at any time.",
                "why_this_matters": "The deal you sign today might not be the deal you have next month.",
                "how_common": "Universal for digital services. Watch for 'notification' emails."
            }
        },
        "DEFAULT": {
            "severity": "MEDIUM",
            "title": "Unilateral Updates",
            "what_is_happening": "They can change the contract terms without your explicit signature.",
            "why_this_matters": "Your obligations could increase over time.",
            "how_common": "Common in online terms; rare in signed bespoke contracts."
        }
    },
    
    "Liability": {
        "DEFAULT": {
            "severity": "MEDIUM",
            "title": "Capped Liability",
            "what_is_happening": "If they cause you a loss (e.g., data breach), their payout is limited.",
            "why_this_matters": "You might not recover the full cost of the damage they cause.",
            "how_common": "Standard business practice, usually capped at 12 months' fees."
        }
    },

    "Dispute Resolution": {
         "TERMS_CONDITIONS": {
            "Consumer": {
                "severity": "MEDIUM",
                "title": "No Lawsuits (Arbitration)",
                "what_is_happening": "You cannot sue them in court or join a class action.",
                "why_this_matters": "Disputes are settled privately. Harder to fight back for small grievances.",
                "how_common": "Very common in US tech contracts to prevent class actions."
            }
        },
        "DEFAULT": {
            "severity": "MEDIUM",
            "title": "Arbitration Clause",
            "what_is_happening": "Disputes go to a private arbitrator, not a public court.",
            "why_this_matters": "Usually faster but limits your appeals and discovery rights.",
            "how_common": "Standard in many modern service agreements."
        }
    },
    
     "Warranty Disclaimer": {
         "TERMS_CONDITIONS": {
            "Consumer": {
                 "severity": "LOW",
                 "title": "No Guarantees",
                 "what_is_happening": "The service is provided 'as is'.",
                 "why_this_matters": "If it breaks, deletes your data, or doesn't work, they aren't legally responsible.",
                 "how_common": "Standard for free software and apps."
            }
         },
         "DEFAULT": {
             "severity": "MEDIUM",
             "title": "No Warranties",
             "what_is_happening": "They disclaim promises about quality or fitness for purpose.",
             "why_this_matters": "You assume the risk of the product not meeting your needs.",
             "how_common": "Standard disclaimer."
         }
     }
}


# =========================================================
# 2. CONTEXT BUILDER
# =========================================================

def build_insight_context(document):
    """
    Constructs the context object used to resolve specific insights.
    """
    doc_type = document.document_type
    
    # 1. Infer Purpose
    # If we already detected purpose in risk_summary (using BERT), we should use it.
    # Since we don't have easy access to that runtime variable here unless we re-run or pass it,
    # we will try to re-infer or use a simplified heuristic if BERT isn't cheap.
    # Fortunately, LegalBERT is fast enough for 2000 chars, but let's try to grab it from attributes if possible.
    # For now, we'll implement a lightweight heuristic mapping doc_type to likely 'Purpose' if not explicit.
    
    purpose = "General"
    
    # Check if we have a detected purpose stored on the doc model (if we added a field)
    # We didn't add a field to the model, it's calculated on the fly.
    # So we will implement a simplified logic here or re-use the engine.
    
    if doc_type in ["NDA_MUTUAL", "NDA_ONEWAY", "NDA"]:
        # Heuristic: Check for 'evaluation' or 'purpose' keywords
        text_lower = document.extracted_text[:3000].lower() if document.extracted_text else ""
        if "evaluat" in text_lower or "potential transaction" in text_lower or "discussions" in text_lower:
            purpose = "Evaluation"
        else:
            purpose = "Ongoing"
            
    elif doc_type == "TERMS_CONDITIONS":
        purpose = "Consumer" # Default for T&Cs usually
        
    elif doc_type == "SERVICE_AGREEMENT":
        purpose = "Ongoing"

    return {
        "document_type": doc_type,
        "purpose": purpose,
        # Future: "relationship_type": ..., "party_orientation": ...
    }


# =========================================================
# 3. INSIGHT RESOLVER
# =========================================================

def generate_insight(pattern_key, context):
    """
    Resolves a specific insight message for a pattern based on context.
    """
    doc_type = context["document_type"]
    purpose = context["purpose"]
    
    # 1. Get Pattern Template
    template = INSIGHT_TEMPLATES.get(pattern_key)
    
    if not template:
        # Fallback if pattern is not in our new system yet
        return {
            "title": pattern_key,
            "severity": "MEDIUM",
            "explanation": f"This document contains a {pattern_key} clause.",
            "what_this_means": "Review this section carefully.",
            "icon": "⚠️"
        }
        
    # 2. Lookup by Doc Type
    doc_block = template.get(doc_type, template.get("DEFAULT"))
    
    # If explicit doc type match failed, fall back to DEFAULT
    if not doc_block:
        doc_block = template.get("DEFAULT")

    # 3. Lookup by Purpose (if doc_block has sub-keys)
    # Note: doc_block might be the final dict (if DEFAULT) or a dict of purposes
    
    # We need to distinguish if doc_block is the leaf node (insight) or a branch (purposes)
    # Check if it has 'what_is_happening' key (new schema) or 'message' (old schema fallback) -> Leaf node
    if "what_is_happening" in doc_block or "message" in doc_block:
        result = doc_block
    else:
        # It's a branch, look up purpose
        result = doc_block.get(purpose, doc_block.get("DEFAULT", doc_block.get("Ongoing", doc_block.get("Consumer"))))
        
        # If still nothing, try to find ANY match or fall back to high-level DEFAULT
        if not result:
            result = template.get("DEFAULT")

    if not result:
        return {
             "title": pattern_key,
             "severity": "MEDIUM",
             "explanation": "Context-specific insight unavailable.",
             "what_this_means": "Standard review recommended.",
             "what_is_happening": "Standard review recommended.",
             "why_this_matters": "Please check this clause.",
             "how_common": "Unknown",
             "icon": "⚠️"
        }

    # Support both new and old keys for backward compatibility if mixed templates exist
    explanation = result.get("what_is_happening") or result.get("message", "")
    implication = result.get("why_this_matters") or result.get("what_this_means", "")

    return {
        "title": result.get("title", pattern_key),
        "explanation": explanation,
        "what_this_means": implication,
        # New keys
        "what_is_happening": explanation,
        "why_this_matters": implication,
        "how_common": result.get("how_common", "Varies by contract type."),
        "severity": result.get("severity", "MEDIUM"),
        "icon": _get_icon_for_pattern(pattern_key)
    }

def _get_icon_for_pattern(pattern):
    icons = {
        "Modifications to Terms": "📝",
        "Termination": "🔄",
        "Liability": "⚠️",
        "Warranty Disclaimer": "🛡️",
        "Dispute Resolution": "⚖️",
        "Indemnification": "💼",
        "Account Security": "🔒",
        "User Obligations": "📋",
        "Privacy & Data": "🔐",
        "Third-Party Services": "🔗",
        "unilateral_indemnification": "💼",
        "one_sided_termination": "⚖️",
    }
    return icons.get(pattern, "⚠️")
