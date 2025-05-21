from sentence_transformers import SentenceTransformer, util
from rapidfuzz import fuzz
import os
from typing import List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)

class SemanticFuzzySearcher:
    def __init__(self, docs: List[str]):
        """Initialize semantic fuzzy searcher with documents.
        
        Args:
            docs: List of document strings to search through
        """
        try:
            self.model = SentenceTransformer("all-MiniLM-L6-v2")
            self.docs = docs
            self.embeddings = self.model.encode(docs, convert_to_tensor=True)
            logger.info(f"Initialized SemanticFuzzySearcher with {len(docs)} documents")
        except Exception as e:
            logger.error(f"Failed to initialize SemanticFuzzySearcher: {e}")
            raise

    def search(self, query: str, top_k: int = 5) -> List[Tuple[str, float]]:
        """Search documents using combined semantic and fuzzy matching.
        
        Args:
            query: Search query string
            top_k: Number of top results to return
            
        Returns:
            List of tuples containing (document, score)
        """
        try:
            query_embedding = self.model.encode(query, convert_to_tensor=True)
            semantic_scores = util.pytorch_cos_sim(query_embedding, self.embeddings)[0]
            
            fuzzy_scores = [fuzz.partial_ratio(query, doc) / 100 for doc in self.docs]
            combined_scores = [(0.6 * sem.item()) + (0.4 * fuzz_score)
                            for sem, fuzz_score in zip(semantic_scores, fuzzy_scores)]
            
            top_indices = sorted(range(len(combined_scores)), 
                               key=lambda i: combined_scores[i], 
                               reverse=True)[:top_k]
            
            return [(self.docs[i], combined_scores[i]) for i in top_indices]
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return [] 