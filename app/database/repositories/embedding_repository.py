"""
Repository for vector embeddings operations.
"""
import logging
import uuid
import numpy as np
from typing import List, Dict, Any, Optional, Tuple

from app.database.models import Embedding
from app.database.config import mongodb_config
from app.database.repositories.base_repository import BaseRepository

logger = logging.getLogger(__name__)

class EmbeddingRepository(BaseRepository[Embedding]):
    """Repository for vector embeddings operations."""
    
    def __init__(self):
        """Initialize the embedding repository."""
        super().__init__(
            collection_name=mongodb_config.embeddings_collection,
            model_class=Embedding
        )
        # Create index for vector similarity search if it doesn't exist
        self._create_indexes()
    
    def _create_indexes(self):
        """Create necessary indexes for the collection."""
        try:
            # Index on document_id for fast lookups
            self.collection.create_index("document_id", unique=True)
            logger.info("Created index on document_id field")
        except Exception as e:
            logger.error(f"Error creating indexes: {str(e)}")
    
    async def find_by_document_id(self, document_id: str) -> Optional[Embedding]:
        """
        Find embedding by document ID.
        
        Args:
            document_id: Document ID
            
        Returns:
            Embedding if found, None otherwise
        """
        results = await self.find({"document_id": document_id}, limit=1)
        return results[0] if results else None
    
    async def add_embedding(self, document_id: str, embedding: List[float], model: str = "arabert") -> Optional[str]:
        """
        Add a new embedding.
        
        Args:
            document_id: Document ID
            embedding: Vector embedding
            model: Model used to generate embedding
            
        Returns:
            Embedding ID if successful, None otherwise
        """
        try:
            # Check if embedding already exists for this document
            existing = await self.find_by_document_id(document_id)
            if existing:
                # Update existing embedding
                await self.update(existing.id, {
                    "embedding": embedding,
                    "embedding_model": model
                })
                return existing.id
            
            # Create new embedding
            embedding_data = {
                "id": f"emb_{uuid.uuid4()}",
                "document_id": document_id,
                "embedding": embedding,
                "embedding_model": model
            }
            
            embedding_obj = Embedding(**embedding_data)
            return await self.create(embedding_obj)
        except Exception as e:
            logger.error(f"Error adding embedding: {str(e)}")
            return None
    
    async def delete_by_document_id(self, document_id: str) -> bool:
        """
        Delete embedding by document ID.
        
        Args:
            document_id: Document ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            result = await self.collection.delete_one({"document_id": document_id})
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"Error deleting embedding: {str(e)}")
            return False
    
    async def find_similar(self, query_embedding: List[float], top_k: int = 5) -> List[Tuple[str, float]]:
        """
        Find documents similar to the query embedding.
        
        Args:
            query_embedding: Query vector embedding
            top_k: Number of results to return
            
        Returns:
            List of (document_id, similarity_score) tuples
        """
        try:
            # Convert query to numpy array
            query_vector = np.array(query_embedding)
            
            # Get all embeddings (for now)
            # In a production system, you'd use vector-specific database 
            # features for this rather than loading all embeddings
            cursor = self.collection.find({})
            results = []
            
            # Calculate similarity for each document
            async for doc in cursor:
                doc_vector = np.array(doc["embedding"])
                # Calculate cosine similarity
                similarity = self._cosine_similarity(query_vector, doc_vector)
                results.append((doc["document_id"], similarity))
            
            # Sort by similarity (descending)
            results.sort(key=lambda x: x[1], reverse=True)
            
            # Return top_k results
            return results[:top_k]
        except Exception as e:
            logger.error(f"Error finding similar documents: {str(e)}")
            return []
    
    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """
        Calculate cosine similarity between two vectors.
        
        Args:
            vec1: First vector
            vec2: Second vector
            
        Returns:
            Cosine similarity score
        """
        try:
            # Normalize vectors
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            return float(np.dot(vec1, vec2) / (norm1 * norm2))
        except Exception as e:
            logger.error(f"Error calculating similarity: {str(e)}")
            return 0.0
