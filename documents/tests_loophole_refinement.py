"""
Tests for loophole detector label verification refinement
Ensures the pass block fix works correctly
"""
import pytest
from django.contrib.auth.models import User
from documents.models import Document, Clause
from documents.loophole_detector import detect_loopholes


@pytest.mark.django_db
class TestLoopholeDetectorRefinement:
    """Test suite for loophole detector label verification"""
    
    def test_missing_clause_detected_when_keyword_exists_but_label_missing(self):
        """
        Test that a clause is flagged as missing when:
        - Keywords exist in text (e.g., "confidential")
        - But no Clause with the expected label exists (e.g., "Confidentiality")
        
        This tests the fix for the pass block that was disabling refinement.
        """
        user = User.objects.create_user(username='testuser', password='pass')
        
        # Create NDA document with "confidential" keyword but no Confidentiality clause
        doc = Document.objects.create(
            user=user,
            title="Weak NDA",
            extracted_text="This agreement covers some confidential stuff but no formal clause.",
            document_type="NDA_MUTUAL",
            processed=True
        )
        
        # Create a clause that mentions "confidential" but is labeled as "Other"
        Clause.objects.create(
            document=doc,
            text="This agreement covers some confidential stuff but no formal clause.",
            label="Other"  # Not "Confidentiality"
        )
        
        # Run loophole detection
        loopholes = detect_loopholes(doc)
        
        # Should detect missing Confidentiality clause
        # because keyword exists but label verification fails
        structural_obs = loopholes.get('structural_observations', [])
        
        # Look for missing confidentiality in structural observations
        missing_confidentiality = any(
            'confidential' in obs.get('category', '').lower() or 
            'confidential' in obs.get('issue', '').lower()
            for obs in structural_obs
        )
        
        # With the fix, this should be detected as missing
        assert missing_confidentiality, "Should detect missing Confidentiality clause despite keyword presence"
    
    def test_clause_not_flagged_when_properly_labeled(self):
        """
        Test that a clause is NOT flagged as missing when:
        - Keywords exist in text
        - AND a properly labeled Clause exists
        """
        user = User.objects.create_user(username='testuser', password='pass')
        
        # Create NDA document with proper Confidentiality clause
        doc = Document.objects.create(
            user=user,
            title="Proper NDA",
            extracted_text="Confidential Information shall mean all proprietary data disclosed by either party.",
            document_type="NDA_MUTUAL",
            processed=True
        )
        
        # Create properly labeled clause
        Clause.objects.create(
            document=doc,
            text="Confidential Information shall mean all proprietary data disclosed by either party.",
            label="Confidentiality"  # Proper label
        )
        
        # Run loophole detection
        loopholes = detect_loopholes(doc)
        
        structural_obs = loopholes.get('structural_observations', [])
        
        # Should NOT flag confidentiality as missing
        missing_confidentiality = any(
            'confidential' in obs.get('category', '').lower()
            for obs in structural_obs
        )
        
        # With proper label, should not be flagged
        assert not missing_confidentiality, "Should NOT flag Confidentiality as missing when properly labeled"
    
    def test_label_verification_for_multiple_expected_clauses(self):
        """
        Test label verification works for multiple expected clauses
        """
        user = User.objects.create_user(username='testuser', password='pass')
        
        # Create NDA with some keywords but missing proper labels
        doc = Document.objects.create(
            user=user,
            title="Incomplete NDA",
            extracted_text="""
            This agreement covers confidential information.
            The term of this agreement is 2 years.
            Parties may not use the information for their own benefit.
            """,
            document_type="NDA_MUTUAL",
            processed=True
        )
        
        # Create clauses with wrong labels
        Clause.objects.create(
            document=doc,
            text="This agreement covers confidential information.",
            label="Other"  # Should be "Confidentiality"
        )
        
        Clause.objects.create(
            document=doc,
            text="The term of this agreement is 2 years.",
            label="Other"  # Should be "Term of Agreement"
        )
        
        Clause.objects.create(
            document=doc,
            text="Parties may not use the information for their own benefit.",
            label="Other"  # Should be "Non-Use Restriction"
        )
        
        # Run loophole detection
        loopholes = detect_loopholes(doc)
        
        structural_obs = loopholes.get('structural_observations', [])
        
        # Should detect multiple missing clauses
        # (keywords exist but labels are wrong)
        assert len(structural_obs) > 0, "Should detect missing clauses despite keyword presence"
