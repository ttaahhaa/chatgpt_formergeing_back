"""
Hybrid retrieval module combining semantic and keyword search.
"""
import logging
import re
from typing import Dict, List, Any, Optional
import numpy as np
from collections import Counter

from app.config import config
from .vector_store_hybrid import get_hybrid_vector_store

logger = logging.getLogger(__name__)

class HybridRetriever:
    """Hybrid retrieval system combining semantic and keyword search."""
    
    def __init__(self, alpha: float = config.HYBRID_ALPHA):
        """Initialize the hybrid retriever.
        
        Args:
            alpha: Weight balancing semantic (1.0) vs keyword (0.0) search
        """
        self.alpha = alpha
        self.vector_store = get_hybrid_vector_store()
        logger.info(f"HybridRetriever initialized with alpha={alpha}")
    
    def _preprocess_query(self, query: str) -> str:
        """Preprocess query for keyword search.
        
        Args:
            query: Original query string
            
        Returns:
            Processed query string
        """
        # Convert to lowercase
        query = query.lower()
        
        # Remove punctuation
        query = re.sub(r'[^\w\s]', ' ', query)
        
        # Remove excess whitespace
        query = re.sub(r'\s+', ' ', query).strip()
        
        return query
    
    def _extract_keywords(self, text: str, top_n: int = 10) -> List[str]:
        """Extract important keywords from text.
        
        Args:
            text: Text to extract keywords from
            top_n: Number of top keywords to extract
            
        Returns:
            List of keywords
        """
        # Simple stopwords list
        stopwords = set([
            'a', 'an', 'the', 'and', 'or', 'but', 'if', 'because', 'as', 'what',
            'when', 'where', 'how', 'why', 'which', 'who', 'whom', 'this', 'that',
            'these', 'those', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
            'have', 'has', 'had', 'having', 'do', 'does', 'did', 'doing', 'i', 'you',
            'he', 'she', 'it', 'we', 'they', 'their', 'his', 'her', 'its', 'our',
            'your', 'my', 'of', 'to', 'in', 'on', 'at', 'for', 'with', 'about'
        ])
        
        # Preprocess text
        text = self._preprocess_query(text)
        
        # Tokenize and count
        words = text.split()
        word_counts = Counter(word for word in words if word not in stopwords and len(word) > 2)
        
        # Get top keywords
        return [word for word, _ in word_counts.most_common(top_n)]
    
    def _keyword_search(self, query: str, documents: List[Dict[str, Any]], k: int = 5) -> List[Dict[str, Any]]:
        """Perform keyword-based search on documents.
        
        Args:
            query: Search query
            documents: List of document dictionaries
            k: Number of results to return
            
        Returns:
            List of documents with scores
        """
        if not documents:
            return []
        
        # Extract keywords from query
        query_keywords = self._extract_keywords(query)
        
        if not query_keywords:
            return documents[:k]  # If no keywords, return the original order
        
        # Score documents based on keyword matches
        scored_docs = []
        for doc in documents:
            text = doc.get('text', '').lower()
            score = 0
            
            # Simple TF scoring
            for keyword in query_keywords:
                score += text.count(keyword)
            
            # Normalize by document length (simple BM25-inspired approach)
            doc_len = len(text.split())
            if doc_len > 0:
                score = score / (0.5 + 0.5 * (doc_len / 500))  # 500 is an arbitrary average doc length
            
            scored_doc = doc.copy()
            scored_doc['keyword_score'] = score
            scored_docs.append(scored_doc)
        
        # Sort by score
        scored_docs = sorted(scored_docs, key=lambda x: x.get('keyword_score', 0), reverse=True)
        
        return scored_docs[:k]
    
    def retrieve(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """Retrieve documents relevant to the query using hybrid approach.
        
        Args:
            query: Search query
            k: Number of results to return
            
        Returns:
            List of relevant documents
        """
        # Semantic search via vector store
        semantic_results = self.vector_store.query(query, top_k=k*2)  # Get more for re-ranking
        
        if not semantic_results:
            logger.warning("No results from semantic search")
            return []
        
        # Keyword search on semantic results
        keyword_results = self._keyword_search(query, semantic_results, k=k*2)
        
        # Hybrid ranking
        if self.alpha == 1.0:
            # Pure semantic search
            results = semantic_results[:k]
        elif self.alpha == 0.0:
            # Pure keyword search
            results = keyword_results[:k]
        else:
            # Hybrid approach - re-rank based on combined scores
            hybrid_results = []
            
            # Create lookup dictionaries for faster access
            semantic_dict = {doc.get('id', doc.get('filename', f"doc_{i}")): (i, doc) for i, doc in enumerate(semantic_results)}
            keyword_dict = {doc.get('id', doc.get('filename', f"doc_{i}")): (i, doc) for i, doc in enumerate(keyword_results)}

            
            # Get all unique document IDs
            all_ids = set(semantic_dict.keys()) | set(keyword_dict.keys())
            
            for doc_id in all_ids:
                semantic_pos = semantic_dict.get(doc_id, (len(semantic_results), None))[0]
                keyword_pos = keyword_dict.get(doc_id, (len(keyword_results), None))[0]
                
                # Normalize positions to [0, 1] range where 0 is best
                semantic_score = 1.0 - (semantic_pos / len(semantic_results) if semantic_pos < len(semantic_results) else 1.0)
                keyword_score = 1.0 - (keyword_pos / len(keyword_results) if keyword_pos < len(keyword_results) else 1.0)
                
                # Combine scores using alpha
                combined_score = (self.alpha * semantic_score) + ((1 - self.alpha) * keyword_score)
                
                # Get the original document
                doc = semantic_dict.get(doc_id, (None, None))[1] or keyword_dict.get(doc_id, (None, None))[1]
                
                if doc:
                    doc_copy = doc.copy()
                    doc_copy['score'] = combined_score
                    hybrid_results.append(doc_copy)
            
            # Sort by combined score
            hybrid_results = sorted(hybrid_results, key=lambda x: x['score'], reverse=True)
            results = hybrid_results[:k]
        
        logger.info(f"Retrieved {len(results)} documents for query: {query}")
        return results

# Create singleton instance
retriever = HybridRetriever()
