"""
Clause Favorability Analysis Module
Analyzes whether clauses favor the user or the other party
Detects one-sided terms and asymmetries
"""

import re
from .models import Clause


def analyze_clause_favorability(clause, document_type):
    """
    Determine if a clause favors the user or counterparty
    
    Args:
        clause: Clause model instance
        document_type: Document type (e.g., 'TERMS_CONDITIONS', 'NDA_MUTUAL')
    
    Returns:
        dict: {
            'risk_level': 'HIGH' | 'MEDIUM' | 'LOW',
            'score': int (positive = unfavorable, negative = favorable),
            'flags': list of concern objects,
            'favorability': 'USER' | 'NEUTRAL' | 'OTHER'
        }
    """
    
    # Unfavorable patterns by document type and clause type
    unfavorable_patterns = {
        'TERMS_CONDITIONS': {
            'termination': [
                (r'terminate.*immediately.*without.*notice', 3, 'Can terminate you without warning'),
                (r'at\s+(our|company\'?s?)\s+sole\s+discretion', 2, 'One-sided control over termination'),
                (r'without\s+cause', 2, 'Can end agreement for any reason'),
                (r'for\s+any\s+reason', 2, 'No justification needed'),
                (r'suspend.*your.*account.*without.*notice', 3, 'Can suspend without warning'),
            ],
            'liability': [
                (r'unlimited\s+liability', 3, 'No cap on your liability'),
                (r'consequential\s+damages', 2, 'Could owe unpredictable damages'),
                (r'indemnify.*for\s+any', 3, 'Very broad indemnification obligation'),
                (r'shall\s+defend.*and.*indemnify', 2, 'Must pay legal costs and damages'),
                (r'liable\s+for\s+all', 2, 'Broad liability scope'),
            ],
            'modification': [
                (r'change.*at\s+any\s+time.*without\s+notice', 3, 'Terms can change without telling you'),
                (r'continued\s+use.*constitutes?\s+acceptance', 2, 'Using service = agreeing to new terms'),
                (r'modify.*in\s+our\s+sole\s+discretion', 2, 'One-sided power to change terms'),
                (r'reserves?\s+the\s+right\s+to\s+modify.*without', 2, 'Can change terms unilaterally'),
            ],
            'payment': [
                (r'non[- ]?refundable', 2, "Can't get money back"),
                (r'automatic(ally)?\s+renew', 2, 'Auto-renewal may be hard to cancel'),
                (r'price.*increase.*at\s+any\s+time', 2, 'Unpredictable cost changes'),
                (r'no\s+refunds?', 2, 'No money back policy'),
            ],
            'indemnification': [
                (r'indemnify.*from\s+any\s+(and\s+)?all', 3, 'Must cover all their losses'),
                (r'defend.*indemnify.*and.*hold\s+harmless', 2, 'Triple protection for them'),
                (r'you.*indemnify.*us.*for.*breach', 2, 'You pay if you breach'),
            ],
            'user obligations': [
                (r'you\s+(shall|must).*comply.*at\s+all\s+times', 2, 'Strict compliance required'),
                (r'solely\s+responsible\s+for', 2, 'All responsibility on you'),
            ],
            'warranty disclaimer': [
                (r'as[- ]?is.*without\s+warrant(y|ies)', 2, 'No guarantees provided'),
                (r'disclaim\s+all\s+warrant(y|ies)', 2, 'They guarantee nothing'),
            ],
        },
        'NDA_MUTUAL': {
            'return or destruction of information': [
                (r'immediately\s+upon\s+request', 2, 'Must return info instantly'),
                (r'certif(y|ication).*destruction', 2, 'Must prove you destroyed info'),
            ],
            'remedies for breach': [
                (r'irreparable\s+harm', 2, 'Breach allows immediate legal action'),
                (r'equitable\s+relief.*without.*bond', 2, 'Can get court order without posting bond'),
            ],
        },
        'SERVICE_AGREEMENT': {
            'payment': [
                (r'non[- ]?refundable', 2, "Can't get money back"),
                (r'late\s+payment.*interest', 2, 'Penalties for late payment'),
            ],
            'liability': [
                (r'client.*indemnif(y|ies)', 2, 'You must cover their losses'),
            ],
        },
    }
    
    # Protective/favorable patterns (reduce risk score)
    protective_patterns = [
        (r'reasonable\s+notice', -1, 'Requires fair warning'),
        (r'mutual(ly)?', -1, 'Applies to both parties equally'),
        (r'limited\s+to', -1, 'Cap on liability or obligations'),
        (r'not\s+(to\s+)?exceed', -1, 'Maximum limit specified'),
        (r'either\s+party\s+may', -1, 'Both sides have same right'),
        (r'with\s+(\d+)\s+days?\s+notice', -1, 'Notice period required'),
        (r'good\s+faith', -1, 'Must act fairly'),
        (r'commercially\s+reasonable', -1, 'Reasonable standard required'),
    ]
    
    risk_score = 0
    flags = []
    
    # Get patterns for this document type
    doc_patterns = unfavorable_patterns.get(document_type, {})
    clause_label = clause.label.lower()
    
    # Check unfavorable patterns for this clause type
    category_patterns = doc_patterns.get(clause_label, [])
    
    for pattern, severity, explanation in category_patterns:
        if re.search(pattern, clause.text, re.IGNORECASE):
            risk_score += severity
            flags.append({
                'type': 'concern',
                'severity': severity,
                'explanation': explanation,
                'pattern': pattern
            })
    
    # Check protective patterns (apply to all clause types)
    for pattern, score_change, explanation in protective_patterns:
        if re.search(pattern, clause.text, re.IGNORECASE):
            risk_score += score_change  # Negative = reduces risk
            flags.append({
                'type': 'protective',
                'severity': score_change,
                'explanation': explanation,
                'pattern': pattern
            })
    
    # Calculate overall assessment
    if risk_score >= 3:
        risk_level = 'HIGH'
        favorability = 'OTHER'
    elif risk_score > 0:
        risk_level = 'MEDIUM'
        favorability = 'NEUTRAL'
    else:
        risk_level = 'LOW'
        favorability = 'USER' if risk_score < 0 else 'NEUTRAL'
    
    return {
        'risk_level': risk_level,
        'score': risk_score,
        'flags': flags,
        'favorability': favorability
    }


def detect_asymmetry(document):
    """
    Find one-sided clauses that favor one party over the other
    
    Args:
        document: Document model instance
    
    Returns:
        list: List of asymmetry objects with details
    """
    
    asymmetries = []
    
    for clause in document.clauses.all():
        text_lower = clause.text.lower()
        
        # Pattern 1: "You must... but we may..."
        you_obligation = bool(re.search(
            r'\b(you|user|customer|subscriber)\s+(shall|must|agree\s+to|are\s+required\s+to)\b', 
            text_lower
        ))
        them_permission = bool(re.search(
            r'\b(we|us|company|service|provider)\s+(may|can|reserves?\s+the\s+right)\b', 
            text_lower
        ))
        
        if you_obligation and them_permission:
            asymmetries.append({
                'clause_id': clause.id,
                'clause_label': clause.label,
                'type': 'obligation_vs_permission',
                'description': 'You have mandatory obligation, they have optional permission',
                'severity': 'HIGH',
                'excerpt': clause.text[:250] + ('...' if len(clause.text) > 250 else '')
            })
        
        # Pattern 2: Different notice periods
        user_notice = re.search(
            r'(you|user|customer).*?(\d+)\s*days?\s*(notice|prior\s+notice)', 
            text_lower
        )
        them_notice = re.search(
            r'(we|us|company|service).*?(\d+)\s*days?\s*(notice|prior\s+notice)', 
            text_lower
        )
        
        if user_notice and them_notice:
            try:
                user_days = int(user_notice.group(2))
                them_days = int(them_notice.group(2))
                
                if user_days > them_days * 1.5:  # You give 50%+ more notice
                    asymmetries.append({
                        'clause_id': clause.id,
                        'clause_label': clause.label,
                        'type': 'notice_period_imbalance',
                        'description': f'You must give {user_days} days notice, they only need {them_days}',
                        'severity': 'MEDIUM',
                        'details': {
                            'user_days': user_days,
                            'them_days': them_days,
                            'ratio': round(user_days / them_days, 1)
                        }
                    })
            except (ValueError, AttributeError):
                pass
        
        # Pattern 3: "You waive... we retain..."
        you_waive = bool(re.search(
            r'(you|user|customer).*?(waive|relinquish|forfeit|give\s+up)', 
            text_lower
        ))
        them_retain = bool(re.search(
            r'(we|us|company|service).*?(retain|reserve|maintain|keep)', 
            text_lower
        ))
        
        if you_waive and them_retain:
            asymmetries.append({
                'clause_id': clause.id,
                'clause_label': clause.label,
                'type': 'rights_imbalance',
                'description': 'You give up rights while they keep theirs',
                'severity': 'HIGH',
                'excerpt': clause.text[:250] + ('...' if len(clause.text) > 250 else '')
            })
        
        # Pattern 4: "You agree to indemnify us"
        unilateral_indemnification = bool(re.search(
            r'(you|user).*?(indemnif(y|ies)|hold\s+harmless).*(us|company|service)', 
            text_lower
        ))
        mutual_indemnification = bool(re.search(
            r'\b(mutual(ly)?|each\s+party|both\s+parties).*?indemnif', 
            text_lower
        ))
        
        if unilateral_indemnification and not mutual_indemnification:
            asymmetries.append({
                'clause_id': clause.id,
                'clause_label': clause.label,
                'type': 'unilateral_indemnification',
                'description': 'You must indemnify them, but they don\'t indemnify you',
                'severity': 'HIGH',
                'excerpt': clause.text[:250] + ('...' if len(clause.text) > 250 else '')
            })
        
        # Pattern 5: Immediate termination for you, notice required for them
        immediate_termination = bool(re.search(
            r'(terminate|suspend).*?(your|user).*?(immediately|without\s+notice)', 
            text_lower
        ))
        
        if immediate_termination and 'termination' in clause.label.lower():
            asymmetries.append({
                'clause_id': clause.id,
                'clause_label': clause.label,
                'type': 'immediate_termination_risk',
                'description': 'They can terminate you immediately without notice',
                'severity': 'HIGH',
                'excerpt': clause.text[:250] + ('...' if len(clause.text) > 250 else '')
            })
    
    return asymmetries


def generate_favorability_summary(document):
    """
    Generate overall favorability summary for the document
    
    Returns:
        dict: Summary with counts and overall assessment
    """
    
    high_risk_count = 0
    medium_risk_count = 0
    low_risk_count = 0
    
    unfavorable_clauses = []
    
    for clause in document.clauses.all():
        analysis = analyze_clause_favorability(clause, document.document_type)
        
        if analysis['risk_level'] == 'HIGH':
            high_risk_count += 1
            unfavorable_clauses.append({
                'clause_id': clause.id,
                'clause_label': clause.label,
                'clause_text': clause.text[:200] + ('...' if len(clause.text) > 200 else ''),
                'risk_level': 'HIGH',
                'score': analysis['score'],
                'flags': analysis['flags']
            })
        elif analysis['risk_level'] == 'MEDIUM':
            medium_risk_count += 1
            unfavorable_clauses.append({
                'clause_id': clause.id,
                'clause_label': clause.label,
                'clause_text': clause.text[:200] + ('...' if len(clause.text) > 200 else ''),
                'risk_level': 'MEDIUM',
                'score': analysis['score'],
                'flags': analysis['flags']
            })
        else:
            low_risk_count += 1
    
    # Overall assessment
    total_clauses = high_risk_count + medium_risk_count + low_risk_count
    
    if total_clauses == 0:
        overall = 'UNKNOWN'
    elif high_risk_count >= 3 or (high_risk_count + medium_risk_count) > total_clauses * 0.4:
        overall = 'UNFAVORABLE'
    elif high_risk_count == 0 and medium_risk_count <= 2:
        overall = 'FAVORABLE'
    else:
        overall = 'NEUTRAL'
    
    return {
        'overall_assessment': overall,
        'high_risk_count': high_risk_count,
        'medium_risk_count': medium_risk_count,
        'low_risk_count': low_risk_count,
        'total_analyzed': total_clauses,
        'unfavorable_clauses': unfavorable_clauses
    }
