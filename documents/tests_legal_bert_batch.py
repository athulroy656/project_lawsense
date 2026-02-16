
from django.test import TestCase
from documents.legal_bert_engine import LegalBertEngine
import numpy as np

class LegalBertBatchTest(TestCase):
    def test_batch_embedding_consistency(self):
        """
        Verify that batched embeddings match single embeddings.
        """
        engine = LegalBertEngine.get_instance()
        texts = [
            "This agreement shall expire on December 31, 2025.",
            "Confidential information must remain secret.",
            "The jurisdiction is New York.",
            "Short text."
        ]
        
        # 1. Get batch embeddings
        batch_embs = engine._get_embedding_batch(texts)
        
        # 2. Get single embeddings
        single_embs = []
        for t in texts:
            single_embs.append(engine._get_embedding(t))
            
        single_embs = np.vstack(single_embs)
        
        # 3. Compare (allow small float diff)
        diff = np.abs(batch_embs - single_embs).max()
        print(f"Max difference between batch and single: {diff}")
        self.assertTrue(diff < 1e-4, "Batch embeddings deviate from single inference!")

    def test_batch_implicit_detection(self):
        """
        Verify batch implicit detection works.
        """
        engine = LegalBertEngine.get_instance()
        texts = [
            "This agreement shall remain in force for one year.", # Duration
            "Parties agree not to disclose proprietary info.",    # Confidentiality
            "Random unrelated text about the weather."            # None
        ]
        
        # Verify parity with single inference
        labels = engine.detect_implicit_clauses_batch(texts)
        single_labels = []
        for t in texts:
             single_labels.append(engine.detect_implicit_clauses(t))

        print(f"Batch Labels: {labels}")
        print(f"Single Labels: {single_labels}")
        
        self.assertEqual(labels, single_labels, "Batch detection results do not match single inference results!")
