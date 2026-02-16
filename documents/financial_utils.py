
import re
import logging
from datetime import datetime

# Attempt to use dateutil for robust parsing if available, else simple regex
try:
    from dateutil import parser as date_parser
except ImportError:
    date_parser = None

from .legal_bert_engine import LegalBertEngine
from .nlp_utils import split_into_clauses

logger = logging.getLogger(__name__)

# --- CONFIGURATION ---
CURRENCY_MAP = {
    "$": "USD", "usd": "USD", "dollars": "USD",
    "€": "EUR", "eur": "EUR", "euros": "EUR",
    "£": "GBP", "gbp": "GBP", "pounds": "GBP",
    "₹": "INR", "inr": "INR", "rupees": "INR",
}

# Regex Patterns
AMOUNT_PATTERN = r"(?:\d{1,3}(?:,\d{3})*|(?:\d+))(?:\.\d{1,2})?(?:[kKmM])?" # Supports 10k, 5M
CURRENCY_SYMBOLS = r"(?:₹|\$|€|£|USD|INR|EUR|GBP|dollars|rupees|euros|pounds)"

PENALTY_KEYWORDS = ["fine", "penalty", "liquidated damages", "late fee", "interest", "surcharge", "cancellation fee"]
EXPIRATION_KEYWORDS = ["expire", "valid until", "remain in force until", "termination date", "end date", "conclude on"]
DURATION_KEYWORDS = ["term", "period", "duration", "validity", "initial term", "remain", "force", "expire"]
LIABILITY_KEYWORDS = ["liability", "cumulative liability", "total liability", "aggregate liability", "cap", "capped", "maximum"]

DURATION_PATTERNS = [
    r"(?:initial\s+)?(?:term|duration|period)\s+(?:of\s+this\s+agreement\s+)?(?:is|shall\s+be)\s+(\d+(?:\.\d+)?\s+(?:year|month|day|week)s?)",
    r"valid\s+(?:for\s+)?(?:a\s+period\s+of\s+)?(\d+(?:\.\d+)?\s+(?:year|month|day|week)s?)",
    r"remain\s+in\s+force\s+(?:for\s+)?(\d+(?:\.\d+)?\s+(?:year|month|day|week)s?)",
    r"expire(?:s)?\s+after\s+(\d+(?:\.\d+)?\s+(?:year|month|day|week)s?)",
    r"(?:term|period).*?\((\d+)\)\s*(?:year|month|day|week)s?", 
    r"\((\d+)\)\s*(?:year|month|day|week)s?"
]

# --- HELPERS ---

def _normalize_value(amount_str):
    """
    Convert string like "10k", "5,000" to float (10000.0, 5000.0).
    """
    clean_str = amount_str.lower().replace(",", "").strip()
    multiplier = 1.0
    
    if clean_str.endswith("k"):
        multiplier = 1000.0
        clean_str = clean_str[:-1]
    elif clean_str.endswith("m"):
        multiplier = 1000000.0
        clean_str = clean_str[:-1]
        
    try:
        return float(clean_str) * multiplier
    except ValueError:
        return 0.0

def _normalize_currency(symbol_or_code):
    """
    Map symbol or word to ISO code.
    """
    return CURRENCY_MAP.get(symbol_or_code.lower(), "USD") # Default USD if unknown symbol matched

def _parse_date_to_iso(date_str):
    """
    Convert date string to YYYY-MM-DD.
    """
    if not date_str: return None
    try:
        # Use dateutil if available for best results
        if date_parser:
            dt = date_parser.parse(date_str, fuzzy=True)
            return dt.strftime("%Y-%m-%d")
        
        # Fallback manual parsing regexes
        # 1. YYYY-MM-DD
        match_iso = re.search(r"(\d{4})-(\d{2})-(\d{2})", date_str)
        if match_iso: return f"{match_iso.group(1)}-{match_iso.group(2)}-{match_iso.group(3)}"
        
        # 2. DD/MM/YYYY
        match_slash = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", date_str)
        if match_slash: return f"{match_slash.group(3)}-{int(match_slash.group(2)):02d}-{int(match_slash.group(1)):02d}"
        
        # 3. DD Month YYYY (e.g. 31st December 2026)
        months = {
            "jan": "01", "feb": "02", "mar": "03", "apr": "04", "may": "05", "jun": "06",
            "jul": "07", "aug": "08", "sep": "09", "oct": "10", "nov": "11", "dec": "12"
        }
        
        match_text = re.search(r"(\d{1,2})(?:st|nd|rd|th)?\s+([a-zA-Z]+).*,?\s+(\d{4})", date_str, re.IGNORECASE)
        if match_text:
            day = int(match_text.group(1))
            month_str = match_text.group(2)[:3].lower()
            year = match_text.group(3)
            if month_str in months:
                return f"{year}-{months[month_str]}-{day:02d}"

        # 4. Month DD, YYYY
        match_text2 = re.search(r"([a-zA-Z]+)\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})", date_str, re.IGNORECASE)
        if match_text2:
            month_str = match_text2.group(1)[:3].lower()
            day = int(match_text2.group(2))
            year = match_text2.group(3)
            if month_str in months:
                return f"{year}-{months[month_str]}-{day:02d}"

        return date_str 
    except:
        return date_str

def extract_monetary_amounts(text):
    """
    Extracts monetary values and normalizes them.
    Returns list of dicts: {currency, value, original}
    """
    results = []
    
    # Pattern 1: Symbol then Amount ($5,000, $10k)
    # Be careful with regex: ensure currency symbol isn't part of a word
    pat1 = f"({CURRENCY_SYMBOLS})\s*({AMOUNT_PATTERN})"
    matches1 = re.findall(pat1, text, re.IGNORECASE)
    
    for symbol, amount in matches1:
        norm_curr = _normalize_currency(symbol)
        norm_val = _normalize_value(amount)
        if norm_val > 0: # Filter zero or parse errors
            results.append({
                "currency": norm_curr,
                "value": norm_val,
                "original": f"{symbol}{amount}"
            })

    # Pattern 2: Amount then Currency (500 dollars, 10k USD)
    pat2 = f"({AMOUNT_PATTERN})\s+({CURRENCY_SYMBOLS})"
    matches2 = re.findall(pat2, text, re.IGNORECASE)
    
    for amount, currency in matches2:
        norm_curr = _normalize_currency(currency)
        norm_val = _normalize_value(amount)
        if norm_val > 0:
            results.append({
                "currency": norm_curr,
                "value": norm_val,
                "original": f"{amount} {currency}"
            })
        
    return results

def extract_expiration_info(document_text):
    """
    Extracts expiration info with ISO date normalization.
    """
    result = {
        "found": False,
        "date": None,
        "iso_date": None,
        "source_text": None,
        "confidence": "Low"
    }
    
    clauses = split_into_clauses(document_text)
    strong_keywords = ["until", "expires on", "remain in force until", "end date", "conclude on", "valid through"]
    
    # Expanded Date Patterns
    DATE_PATS = [
        r"\b\d{1,2}(?:st|nd|rd|th)?\s+(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?),?\s+\d{4}\b",
        r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4}\b",
        r"\b\d{4}-\d{2}-\d{2}\b",
        r"\b\d{2}/\d{2}/\d{4}\b"
    ]
    
    for clause in clauses:
        lower_clause = clause.lower()
        if any(kw in lower_clause for kw in strong_keywords):
            matches = []
            for pat in DATE_PATS:
                for m in re.finditer(pat, clause, re.IGNORECASE):
                    matches.append((m.start(), m.group(0)))
            
            # Sort by position, take last
            matches.sort(key=lambda x: x[0])
            if matches:
                date_str = matches[-1][1]
                result["found"] = True
                result["date"] = date_str
                result["iso_date"] = _parse_date_to_iso(date_str)
                result["source_text"] = clause.strip()
                result["confidence"] = "High"
                return result

    # Fallback
    for clause in clauses:
        lower_clause = clause.lower()
        if "effective" in lower_clause and not any(kw in lower_clause for kw in strong_keywords):
            continue
            
        if any(kw in lower_clause for kw in EXPIRATION_KEYWORDS):
             for pat in DATE_PATS:
                match = re.search(pat, clause, re.IGNORECASE)
                if match:
                    date_str = match.group(0)
                    result["found"] = True
                    result["date"] = date_str
                    result["iso_date"] = _parse_date_to_iso(date_str)
                    result["source_text"] = clause.strip()
                    result["confidence"] = "Medium"
                    return result

    return result

def extract_penalties(document_text, doc_type="OTHER", purpose="Unknown"):
    """
    Extracts penalties, strictly filtering for financial/numeric ones.
    """
    penalties = []
    clauses = split_into_clauses(document_text)
    seen_amounts = set() # Simple deduplication
    
    for clause in clauses:
        lower_clause = clause.lower()
        
        # Negative Checks
        if any(pha in lower_clause for pha in ["no penalty", "no monetary penalty", "without penalty"]):
            continue

        if any(kw in lower_clause for kw in PENALTY_KEYWORDS):
             # Hard Filter: Must contain a number or specific "liquidated damages" phrase
             monetary = extract_monetary_amounts(clause)
             
             # If no money found, check if it's explicitly "liquidated damages"
             if not monetary:
                 if "liquidated damages" not in lower_clause:
                     continue
                 amount_disp = "See clause (Liquidated Damages)"
                 val = 0.0
             else:
                 # Use first found amount
                 m = monetary[0]
                 # Deduplicate by value
                 if m["value"] in seen_amounts: continue
                 seen_amounts.add(m["value"])
                 
                 amount_disp = m["original"]
                 val = m["value"]

             penalties.append({
                 "type": "Financial Penalty",
                 "amount": amount_disp,
                 "amount_value": val,
                 "condition": "Violation",
                 "severity": "Medium" if val < 10000 else "High", 
                 "source_text": clause.strip()
             })

    return penalties 

def extract_liability_caps(document_text):
    """
    Extracts liability caps: fixed amounts, percentages, or formulas.
    """
    result = {
        "found": False,
        "amount": None,      # Structured amount if fixed
        "percentage": None,  # Float if percentage
        "expression": None,  # Text description
        "source": None
    }
    
    clauses = split_into_clauses(document_text)
    
    for clause in clauses:
        lower_clause = clause.lower()
        if any(kw in lower_clause for kw in LIABILITY_KEYWORDS):
             if any(cap_kw in lower_clause for cap_kw in ["not exceed", "capped at", "limited to", "maximum amount", "aggregate liability", "total liability"]):
                 
                 # 1. Check for "Greater/Lesser of X or Y" (Formula)
                 if "greater of" in lower_clause or "lesser of" in lower_clause or "whichever is higher" in lower_clause:
                     result["found"] = True
                     
                     # Try to capture the specific formula part
                     # e.g. "greater of $10,000 or fees paid"
                     match_phrase = re.search(r"(greater|lesser) of .*?(or|and) .*?(paid|fees|contract|\$)", lower_clause)
                     if match_phrase:
                         # Capture reasonably long segment
                         start = match_phrase.start()
                         end = min(len(lower_clause), start + 50)
                         phrase = clause[start:end].strip()
                         # Clean ending punctuation
                         phrase = phrase.rstrip(".,;)")
                     else:
                         phrase = clause.strip()

                     result["expression"] = phrase
                     result["source"] = clause.strip()
                     return result

                 # 2. Check for Percentage ("10% of fees")
                 pct_match = re.search(r"(\d+(?:\.\d+)?)\s*%", clause)
                 if pct_match and ("fees" in lower_clause or "paid" in lower_clause or "contract" in lower_clause):
                     result["found"] = True
                     result["percentage"] = float(pct_match.group(1))
                     result["expression"] = clause.strip()
                     result["source"] = clause.strip()
                     return result

                 # 3. Check for Fixed Amount
                 amounts = extract_monetary_amounts(clause)
                 if amounts:
                     # Pick the largest amount if multiple found (usually the cap)
                     best_amount = max(amounts, key=lambda x: x["value"])
                     result["found"] = True
                     result["amount"] = best_amount # Entire structured dict
                     result["expression"] = best_amount["original"] # Text representation
                     result["source"] = clause.strip()
                     return result
                 
                 # 4. Fallback: "Fees paid" without number
                 if "fees paid" in lower_clause or "amount paid" in lower_clause:
                      result["found"] = True
                      result["expression"] = "Fees paid (Variable)"
                      result["source"] = clause.strip()
                      return result

    return result

def extract_deadlines(document_text):
    """
    Extracts operational deadlines (e.g., return within X days).
    """
    deadlines = []
    clauses = split_into_clauses(document_text)
    
    # Patterns for deadlines
    # We want to capture the time period: "7 days", "30 days"
    deadline_patterns = [
        # "within X days"
        r"within\s+(?:[a-zA-Z-]+\s+)?\(?(\d+(?:\.\d+)?)\)?\s+(?:business\s+)?(?:day|week|month)s?",
        # "no later than X days"
        r"no\s+later\s+than\s+(?:[a-zA-Z-]+\s+)?\(?(\d+(?:\.\d+)?)\)?\s+(?:business\s+)?(?:day|week|month)s?",
        # "X days notice"
        r"(?:[a-zA-Z-]+\s+)?\(?(\d+(?:\.\d+)?)\)?\s+(?:business\s+)?(?:day|week|month)s?['’]?\s+notice",
        # "cure period of X days"
        r"cure\s+period\s+of\s+(?:[a-zA-Z-]+\s+)?\(?(\d+(?:\.\d+)?)\)?\s+(?:business\s+)?(?:day|week|month)s?",
        # "return... within X days"
        r"(?:return|destroy|deliver|pay)\s+(?:within\s+)?(?:[a-zA-Z-]+\s+)?\(?(\d+(?:\.\d+)?)\)?\s+(?:business\s+)?(?:day|week|month)s?"
    ]

    for clause in clauses:
        lower_clause = clause.lower()
        matched = False
        for pat in deadline_patterns:
            match = re.search(pat, lower_clause)
            if match:
                time_val = match.group(0)
                if len(match.groups()) > 0:
                     time_val = match.group(1)
                
                action = "General Obligation"
                if "return" in lower_clause or "destroy" in lower_clause: action = "Return/Destroy Info"
                elif "notice" in lower_clause or "notify" in lower_clause: action = "Provide Notice"
                elif "cure" in lower_clause: action = "Cure Breach"
                elif "pay" in lower_clause or "invoice" in lower_clause: action = "Payment"
                
                trigger = "Specified event"
                if "termination" in lower_clause: trigger = "Termination"
                if "request" in lower_clause: trigger = "Written Request"
                
                deadlines.append({
                    "time": time_val.strip(),
                    "trigger": trigger,
                    "action": action,
                    "source": clause.strip()
                })
                matched = True
                break
        if matched: continue
    return deadlines

def extract_duration(document_text):
    """
    Extracts duration using strict context gating to avoid false positives.
    """
    result = {
        "found": False,
        "term": None,
        "source": None
    }
    
    clauses = split_into_clauses(document_text)
    
    STRONG_ANCHORS = [
        "initial term", "term of this agreement", "remain in force", 
        "valid for", "validity period", "continue for", 
        "renewal term", "duration of this agreement"
    ]
    WEAK_ANCHORS = [ "expire", "expiry", "expiration", "termination", "effective date" ]
    WEAK_CONTEXT_REQUIRED = ["until", "on", "for", "after"]
    exclusion_phrases = ["within", "no later than", "receipt", "invoice", "payment due", "remedy", "written notice", "written request"]

    for clause in clauses:
        lower_clause = clause.lower()
        if not any(kw in lower_clause for kw in DURATION_KEYWORDS): continue
        if any(ex in lower_clause for ex in exclusion_phrases): continue

        has_strong = any(anchor in lower_clause for anchor in STRONG_ANCHORS)
        has_weak = any(anchor in lower_clause for anchor in WEAK_ANCHORS)
        
        is_valid_anchor = False
        if has_strong: is_valid_anchor = True
        elif has_weak:
            if any(ctx in lower_clause for ctx in WEAK_CONTEXT_REQUIRED):
                is_valid_anchor = True
        if not is_valid_anchor: continue

        for pat in DURATION_PATTERNS:
            match = re.search(pat, lower_clause)
            if match:
                term_val = match.group(1) if len(match.groups()) > 0 else match.group(0)
                full_match = match.group(0)
                if ")" in full_match and "(" in lower_clause: 
                     unit_match = re.search(r"(year|month|day|week)s?", full_match)
                     if unit_match: term_val = f"{term_val} {unit_match.group(0)}"
                     else: term_val = f"{term_val} months" 
                
                result["term"] = term_val
                result["found"] = True
                result["source"] = clause.strip()
                return result
    return result

def extract_all_financial_data(text):
    """
    Aggregates all financial data into the structured JSON format.
    """
    exp_info = extract_expiration_info(text)
    expiration_data = {
        "found": exp_info["found"],
        "date": exp_info["date"],
        "iso_date": exp_info.get("iso_date"), 
        "source": exp_info.get("source_text") or exp_info.get("source")
    }
    
    return {
        "expiration": expiration_data,
        "duration": extract_duration(text),
        "penalties": extract_penalties(text),
        "liability_cap": extract_liability_caps(text),
        "deadlines": extract_deadlines(text)
    }
