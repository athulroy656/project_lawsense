"""
Security tests for Q&A document isolation
Tests that Q&A queries are properly scoped to specific documents
and cannot leak data across documents or users.
"""
import pytest
from django.contrib.auth.models import User
from documents.models import Document, Clause
from documents.vector_utils import index_clauses
from documents.qa_utils import answer_question, retrieve_clauses


@pytest.mark.django_db
class TestQAIsolation:
    """Test suite for Q&A document isolation security"""
    
    def setup_method(self):
        """Create test users and documents"""
        # Create two users
        self.user1 = User.objects.create_user(username='user1', password='pass1')
        self.user2 = User.objects.create_user(username='user2', password='pass2')
        
        # Create two documents with different termination fees
        self.doc1 = Document.objects.create(
            user=self.user1,
            title="Contract A",
            extracted_text="Termination fee is $500. Early termination requires 30 days notice.",
            document_type="SERVICE_AGREEMENT",
            processed=True
        )
        
        self.doc2 = Document.objects.create(
            user=self.user2,
            title="Contract B",
            extracted_text="Termination fee is $2000. Immediate termination allowed with penalty.",
            document_type="SERVICE_AGREEMENT",
            processed=True
        )
        
        # Create clauses for doc1
        self.clause1 = Clause.objects.create(
            document=self.doc1,
            text="Termination fee is $500. Early termination requires 30 days notice.",
            label="Termination"
        )
        
        # Create clauses for doc2
        self.clause2 = Clause.objects.create(
            document=self.doc2,
            text="Termination fee is $2000. Immediate termination allowed with penalty.",
            label="Termination"
        )
        
        # Index clauses in vector store
        index_clauses(self.doc1)
        index_clauses(self.doc2)
    
    def test_retrieve_clauses_filters_by_document_id(self):
        """Test that retrieve_clauses only returns clauses from the specified document"""
        question = "What is the termination fee?"
        
        # Query for doc1
        results_doc1 = retrieve_clauses(question, document_id=self.doc1.id, user_id=self.user1.id)
        
        # Should only get clauses from doc1
        assert len(results_doc1) > 0
        for doc in results_doc1:
            assert doc.metadata['document_id'] == self.doc1.id
            assert "$500" in doc.page_content or "30 days" in doc.page_content
            assert "$2000" not in doc.page_content  # Should NOT contain doc2 data
    
    def test_retrieve_clauses_filters_by_user_id(self):
        """Test that retrieve_clauses respects user_id filtering"""
        question = "What is the termination fee?"
        
        # Query for doc2 with user2
        results_doc2 = retrieve_clauses(question, document_id=self.doc2.id, user_id=self.user2.id)
        
        # Should only get clauses from doc2
        assert len(results_doc2) > 0
        for doc in results_doc2:
            assert doc.metadata['document_id'] == self.doc2.id
            assert doc.metadata.get('user_id') == self.user2.id
            assert "$2000" in doc.page_content
            assert "$500" not in doc.page_content  # Should NOT contain doc1 data
    
    def test_answer_question_scoped_to_document(self):
        """Test that answer_question returns answers only from the specified document"""
        question = "What is the termination fee?"
        
        # Query doc1
        answer1 = answer_question(
            question, 
            document_id=self.doc1.id, 
            user_id=self.user1.id,
            document_type=self.doc1.document_type
        )
        
        # Extract answer text
        answer_text1 = answer1.get('answer', '') if isinstance(answer1, dict) else str(answer1)
        
        # Should mention $500, not $2000
        assert "$500" in answer_text1 or "500" in answer_text1
        assert "$2000" not in answer_text1
        assert "2000" not in answer_text1
    
    def test_cross_document_leakage_prevention(self):
        """
        CRITICAL SECURITY TEST: Ensure user A querying doc A 
        never receives data from doc B
        """
        question = "What is the termination fee?"
        
        # User 1 queries their document
        answer1 = answer_question(
            question,
            document_id=self.doc1.id,
            user_id=self.user1.id,
            document_type=self.doc1.document_type
        )
        
        # User 2 queries their document
        answer2 = answer_question(
            question,
            document_id=self.doc2.id,
            user_id=self.user2.id,
            document_type=self.doc2.document_type
        )
        
        # Extract answer texts
        answer_text1 = answer1.get('answer', '') if isinstance(answer1, dict) else str(answer1)
        answer_text2 = answer2.get('answer', '') if isinstance(answer2, dict) else str(answer2)
        
        # User 1 should NEVER see user 2's data
        assert "$2000" not in answer_text1
        assert "2000" not in answer_text1
        
        # User 2 should NEVER see user 1's data
        assert "$500" not in answer_text2
        assert "500" not in answer_text2
    
    def test_guest_user_document_isolation(self):
        """Test that guest users (user_id=None) still get document-scoped results"""
        # Create a guest document (no user)
        guest_doc = Document.objects.create(
            user=None,
            title="Guest Contract",
            extracted_text="Termination fee is $100. No notice required.",
            document_type="TERMS_CONDITIONS",
            processed=True
        )
        
        guest_clause = Clause.objects.create(
            document=guest_doc,
            text="Termination fee is $100. No notice required.",
            label="Termination"
        )
        
        index_clauses(guest_doc)
        
        question = "What is the termination fee?"
        
        # Guest query (user_id=None)
        answer = answer_question(
            question,
            document_id=guest_doc.id,
            user_id=None,
            document_type=guest_doc.document_type
        )
        
        answer_text = answer.get('answer', '') if isinstance(answer, dict) else str(answer)
        
        # Should only see guest doc data
        assert "$100" in answer_text or "100" in answer_text
        assert "$500" not in answer_text
        assert "$2000" not in answer_text
