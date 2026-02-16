"""
Question Suggestions Module
Generates relevant question suggestions based on document type and detected clauses
"""


def suggest_questions(document):
    """
    Suggest relevant questions users might ask based on document
    
    Args:
        document: Document model instance
    
    Returns:
        list: List of suggested question strings (max 6)
    """
    
    suggestions = []
    doc_type = document.document_type
    
    # Base suggestions by document type
    type_suggestions = {
        'NDA_MUTUAL': [
            "What information is considered confidential?",
            "How long does my confidentiality obligation last?",
            "Can I share confidential information with my employees?",
            "What happens if I accidentally disclose something?",
            "When can I stop keeping information confidential?",
            "What are the exclusions from confidential information?"
        ],
        'NDA_ONEWAY': [
            "What information is considered confidential?",
            "How long must I keep information confidential?",
            "Can I share confidential info with my team?",
            "What happens if confidential info is breached?",
            "What information is excluded from confidentiality?",
            "Do I need to return confidential materials?"
        ],
        'TERMS_CONDITIONS': [
            "Can they change these terms without notice?",
            "How do I cancel my account?",
            "Who owns the content I upload?",
            "What am I liable for?",
            "How are disputes resolved?",
            "Are there any age restrictions?"
        ],
        'SERVICE_AGREEMENT': [
            "What services are included?",
            "How and when do I need to pay?",
            "How can I terminate the agreement?",
            "What are the deliverables?",
            "Who is responsible for delays?",
            "What happens if there's a dispute?"
        ],
        'PRIVACY_POLICY': [
            "What personal data is collected?",
            "How is my data used?",
            "Who can access my data?",
            "Can I delete my data?",
            "How is my data protected?",
            "Are cookies used?"
        ],
        'EMPLOYMENT_AGREEMENT': [
            "What is my salary and compensation?",
            "What are my job responsibilities?",
            "How much notice is required to quit?",
            "What benefits am I entitled to?",
            "Can I work for competitors after leaving?",
            "What happens if I'm terminated?"
        ]
    }
    
    # Get base suggestions for document type
    suggestions = type_suggestions.get(doc_type, [
        "What are the key terms of this agreement?",
        "How can this agreement be terminated?",
        "What are my main obligations?",
        "What happens if there's a breach?",
        "Who is responsible for disputes?",
        "Can this agreement be modified?"
    ])
    
    # Add clause-specific suggestions based on what's detected
    clause_labels = list(document.clauses.values_list('label', flat=True))
    clause_specific_suggestions = []
    
    if 'Payment' in clause_labels:
        clause_specific_suggestions.append("What are the payment terms and conditions?")
    
    if 'Liability' in clause_labels:
        clause_specific_suggestions.append("What is my maximum liability under this agreement?")
    
    if 'Termination' in clause_labels:
        clause_specific_suggestions.append("How can either party terminate this agreement?")
    
    if 'Intellectual Property' in clause_labels:
        clause_specific_suggestions.append("Who owns the intellectual property rights?")
    
    if 'Indemnification' in clause_labels:
        clause_specific_suggestions.append("What do I need to indemnify them for?")
    
    if 'Force Majeure' in clause_labels:
        clause_specific_suggestions.append("What happens in case of force majeure events?")
    
    if 'Confidentiality' in clause_labels:
        clause_specific_suggestions.append("What confidentiality obligations do I have?")
    
    if 'Dispute Resolution' in clause_labels:
        clause_specific_suggestions.append("How are disputes handled?")
    
    if 'Warranty Disclaimer' in clause_labels:
        clause_specific_suggestions.append("What warranties are provided or disclaimed?")
    
    if 'User Content' in clause_labels:
        clause_specific_suggestions.append("What rights do they have to my content?")
    
    if 'Acceptable Use' in clause_labels:
        clause_specific_suggestions.append("What activities are prohibited?")
    
    if 'Amendment' in clause_labels or 'Modifications to Terms' in clause_labels:
        clause_specific_suggestions.append("Can they modify this agreement?")
    
    # Combine base suggestions with clause-specific ones
    # Prioritize clause-specific suggestions
    combined = clause_specific_suggestions + suggestions
    
    # Remove duplicates while preserving order
    seen = set()
    unique_suggestions = []
    for suggestion in combined:
        if suggestion.lower() not in seen:
            seen.add(suggestion.lower())
            unique_suggestions.append(suggestion)
    
    # Return max 6 suggestions
    return unique_suggestions[:6]
