try:
    import torch
    from transformers import AutoTokenizer, AutoModel
    import numpy as np
    from sklearn.metrics.pairwise import cosine_similarity
    BERT_AVAILABLE = True
except ImportError:
    BERT_AVAILABLE = False
    torch = None
    AutoTokenizer = None
    AutoModel = None
    np = None
    cosine_similarity = None

from functools import lru_cache

# Define PURPOSE categories and reference texts (as per design)
PURPOSE_CATEGORIES = {
    "Evaluation / One-time disclosure": [
        "This agreement is entered solely for evaluation of a potential business relationship.",
        "The purpose of this disclosure is to evaluate a potential transaction.",
        "Parties wish to explore a business opportunity.",
    ],
    "Ongoing business relationship": [
        "The parties intend to engage in an ongoing commercial relationship.",
        "This agreement governs the supply of goods and services over a term.",
        "Master Services Agreement for recurring services.",
    ],
    "Employment / Service engagement": [
        "This agreement governs the terms of employment between the parties.",
        "Contractor agrees to provide services to the Company.",
        "Employment contract outlining duties and compensation.",
    ],
    "Licensing / IP usage": [
        "Licensor grants Licensee a right to use the software.",
        "This agreement controls the use of intellectual property rights.",
        "End User License Agreement.",
    ],
    "General policy disclosure": [
        "This policy explains how we collect and use data.",
        "Terms of use for the website.",
        "Privacy policy and data protection terms.",
    ]
}

# Define IMPLICIT CLAUSE types and reference texts (as per design)
IMPLICIT_CLAUSE_REFERENCES = {
    "Termination": [
        "Either party may terminate this agreement with written notice.",
        "This agreement shall terminate upon completion of services.",
    ],
    "Confidentiality": [
        "Recipient shall keep the information confidential.",
        "Parties agree not to disclose proprietary information.",
    ],
    "Governing Law": [
        "This agreement shall be governed by the laws of the State.",
        "Jurisdiction for disputes shall be the courts.",
    ],
    "Duration": [
        "This agreement shall remain in effect for one year.",
        "The term of this agreement is 12 months.",
    ],
    "Penalty": [
        "A penalty of $500 shall apply for late payment.",
        "Liquidated damages in the amount of $1000.",
        "User agrees to pay a fine for violation of terms.",
        "Late fee of 1.5% per month.",
    ],
    "Expiration": [
        "This agreement expires on December 31, 2025.",
        "The validity of this offer ends on the expiration date.",
        "This contract shall remain in force until terminated.",
    ]
}

class LegalBertEngine:
    _instance = None
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        # Use a smaller variant if memory is an issue, but user asked for Legal-BERT.
        # nlpaueb/legal-bert-base-uncased is the standard.
        self.model_name = "nlpaueb/legal-bert-base-uncased"
        print(f"Loading {self.model_name}...")
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self.model = AutoModel.from_pretrained(self.model_name)
        self.model.eval()  # Set to evaluation mode
        
        # Precompute embeddings
        self.purpose_embeddings = self._precompute_embeddings(PURPOSE_CATEGORIES)
        self.clause_embeddings = self._precompute_embeddings(IMPLICIT_CLAUSE_REFERENCES)
        print("Legal-BERT Engine initialized.")

    def _get_embedding_batch(self, texts, batch_size=32):
        """
        Batched embedding generation.
        """
        all_embeddings = []
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]
            inputs = self.tokenizer(batch_texts, return_tensors="pt", truncation=True, max_length=512, padding=True)
            with torch.no_grad():
                outputs = self.model(**inputs)
            # Use CLS token embedding (index 0)
            cls_embeddings = outputs.last_hidden_state[:, 0, :].numpy()
            all_embeddings.append(cls_embeddings)
        
        if not all_embeddings:
            return np.array([])
        return np.vstack(all_embeddings)

    def _precompute_embeddings(self, category_dict):
        embeddings = {}
        for category, texts in category_dict.items():
            # Create a prototype embedding by averaging the reference texts
            # Use batch for efficiency
            emb_matrix = self._get_embedding_batch(texts)
            # Average the vectors
            if len(emb_matrix) > 0:
                avg_emb = np.mean(emb_matrix, axis=0).reshape(1, -1)
                embeddings[category] = avg_emb
            else:
                embeddings[category] = np.zeros((1, 768)) # Fallback size
        return embeddings

    def _get_embedding(self, text):
        # Delegate to batch for consistency check, though single use is fine
        return self._get_embedding_batch([text])[0]

    def detect_implicit_clauses_batch(self, clause_texts, threshold=0.65):
        """
        Detects implicit clauses for a batch of texts.
        Returns a list of labels (or None if no match).
        """
        # Filter out short texts first to save compute
        valid_indices = [i for i, text in enumerate(clause_texts) if text and len(text.split()) >= 5]
        valid_texts = [clause_texts[i] for i in valid_indices]

        if not valid_texts:
            return [None] * len(clause_texts)

        # Get embeddings in batch
        text_embs = self._get_embedding_batch(valid_texts)

        results_map = {} # index -> label

        for idx, text_emb in zip(valid_indices, text_embs):
            best_match = None
            max_sim = threshold
            
            # Compare against reference centroids
            for clause_type, ref_emb in self.clause_embeddings.items():
                sim = cosine_similarity(text_emb.reshape(1, -1), ref_emb)[0][0]
                if sim > max_sim:
                    max_sim = sim
                    best_match = clause_type
            
            results_map[idx] = best_match

        # Reassemble full results list
        final_results = []
        for i in range(len(clause_texts)):
            final_results.append(results_map.get(i, None))
            
        return final_results

    def detect_implicit_clauses(self, clause_text, threshold=0.65):
        return self.detect_implicit_clauses_batch([clause_text], threshold)[0]
    
    def compute_similarity(self, text1, text2):
        embs = self._get_embedding_batch([text1, text2])
        return float(cosine_similarity(embs[0].reshape(1, -1), embs[1].reshape(1, -1))[0][0])
    
    def retrieve_similar_clauses(self, document, clause_description, top_k=3):
        """
        Retrieve semantically similar clause paragraphs from document using ChromaDB.
        Used for semantic fallback when regex detection fails.
        
        Args:
            document: Document model instance
            clause_description: Description of the clause to search for
            top_k: Number of top results to return
            
        Returns:
            list: List of dicts with {text, score} for top matches
        """
        try:
            from .chroma_utils import get_chroma_client
            
            # Get ChromaDB collection for this document
            client = get_chroma_client()
            collection_name = f"doc_{document.id}_clauses"
            
            try:
                collection = client.get_collection(name=collection_name)
            except Exception:
                # Collection doesn't exist - document not indexed yet
                return []
            
            # Query using clause description
            results = collection.query(
                query_texts=[clause_description],
                n_results=min(top_k, collection.count())
            )
            
            if not results or not results.get('documents'):
                return []
            
            # Format results
            similar_clauses = []
            for i, doc_text in enumerate(results['documents'][0]):
                distance = results['distances'][0][i] if 'distances' in results else 1.0
                # Convert distance to similarity score (lower distance = higher similarity)
                score = 1.0 - min(distance, 1.0)
                
                similar_clauses.append({
                    'text': doc_text,
                    'score': score
                })
            
            return similar_clauses
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error retrieving similar clauses: {e}")
            return []
