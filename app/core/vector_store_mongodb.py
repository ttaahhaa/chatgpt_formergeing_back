"""
MongoDB-based vector store for document embeddings.
Replaces the file-based vector store with a MongoDB implementation.
"""
import logging
import numpy as np
import uuid
from typing import List, Dict, Any, Optional, Tuple
import asyncio

from app.core.embeddings import Embeddings
from app.database.repositories.factory import repository_factory

logger = logging.getLogger(__name__)

class MongoDBVectorStore:
    """Class for managing vector embeddings of documents in MongoDB."""
    
    def __init__(self):
        """Initialize the MongoDB vector store."""
        self.embeddings_model = Embeddings()  # Use ArabERT by default
        self.document_repo = repository_factory.document_repository
        self.embedding_repo = repository_factory.embedding_repository
        logger.info("Initialized MongoDB vector store")
    
    async def add_document(self, document: Dict[str, Any]) -> bool:
        """
        Add a document to the vector store.
        
        Args:
            document: Document data including content and metadata
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Generate a unique document ID if not present
            if "id" not in document:
                document["id"] = f"doc_{uuid.uuid4()}"
            
            # Check if document already exists by filename
            existing = await self.document_repo.find_by_filename(document.get("filename", ""))
            if existing:
                logger.info(f"Document already exists: {document.get('filename', '')}")
                return True
            
            # Add document to database
            doc_id = await self.document_repo.add_document(document)
            
            if not doc_id:
                logger.error("Failed to add document to database")
                return False
            
            # Generate embedding for document content
            content = document.get("content", "")
            if content:
                embedding = self.embeddings_model.get_embeddings(content)
                
                # Add embedding to database
                emb_id = await self.embedding_repo.add_embedding(
                    document_id=doc_id,
                    embedding=embedding[0].tolist() if hasattr(embedding[0], "tolist") else embedding[0],
                    model="arabert"
                )
                
                if not emb_id:
                    logger.warning(f"Failed to add embedding for document {doc_id}")
            
            logger.info(f"Added document: {document.get('filename', 'unknown')}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding document: {str(e)}")
            return False
    
    async def clear(self) -> bool:
        """
        Clear all documents from the vector store.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get all documents
            documents = await self.document_repo.find({})
            
            success = True
            # Delete each document and its embedding
            for doc in documents:
                # Delete embedding first (to maintain referential integrity)
                emb_deleted = await self.embedding_repo.delete_by_document_id(doc.id)
                
                # Delete document
                doc_deleted = await self.document_repo.delete(doc.id)
                
                if not doc_deleted:
                    logger.warning(f"Failed to delete document {doc.id}")
                    success = False
            
            logger.info("Cleared vector store")
            return success
            
        except Exception as e:
            logger.error(f"Error clearing vector store: {str(e)}")
            return False
    
    async def get_documents(self) -> List[Dict[str, Any]]:
        """
        Get all documents in the vector store.
        
        Returns:
            List of documents
        """
        try:
            documents = await self.document_repo.find({})
            
            # Convert to dictionary format
            return [doc.dict() for doc in documents]
            
        except Exception as e:
            logger.error(f"Error getting documents: {str(e)}")
            return []
    
    async def query(self, query_text: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Query the vector store for relevant documents.
        
        Args:
            query_text: Query text
            top_k: Number of top results to return
            
        Returns:
            List of relevant documents with scores
        """
        try:
            if not query_text:
                return []
            
            # Generate embedding for the query
            query_embedding = self.embeddings_model.get_embeddings(query_text)[0]
            
            # Find similar documents
            similar_docs = await self.embedding_repo.find_similar(
                query_embedding=query_embedding.tolist() if hasattr(query_embedding, "tolist") else query_embedding,
                top_k=top_k
            )
            
            if not similar_docs:
                return []
            
            # Get full documents for the results
            results = []
            for doc_id, score in similar_docs:
                document = await self.document_repo.find_by_id(doc_id)
                if document:
                    # Convert to dictionary and add score
                    doc_dict = document.dict()
                    doc_dict["score"] = float(score)
                    results.append(doc_dict)
            
            logger.info(f"Query: '{query_text}' returned {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"Error querying vector store: {str(e)}")
            return []
    
    async def get_document_by_id(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a document by its ID.
        
        Args:
            doc_id: Document ID
            
        Returns:
            Document if found, None otherwise
        """
        try:
            document = await self.document_repo.find_by_id(doc_id)
            if document:
                return document.dict()
            return None
            
        except Exception as e:
            logger.error(f"Error getting document by ID: {str(e)}")
            return None
    
    async def get_document_by_filename(self, filename: str) -> Optional[Dict[str, Any]]:
        """
        Get a document by its filename.
        
        Args:
            filename: Document filename
            
        Returns:
            Document if found, None otherwise
        """
        try:
            document = await self.document_repo.find_by_filename(filename)
            if document:
                return document.dict()
            return None
            
        except Exception as e:
            logger.error(f"Error getting document by filename: {str(e)}")
            return None

# Create sync wrapper functions for backward compatibility
class VectorStoreMongoDB:
    """
    Synchronous wrapper around the async MongoDBVectorStore.
    Maintains compatibility with the existing API.
    """
    
    def __init__(self):
        """Initialize the sync vector store."""
        self.async_store = MongoDBVectorStore()
        self.documents = []  # Cache for compatibility
        self.document_embeddings = []  # Cache for compatibility
        logger.info("Initialized synchronous MongoDB vector store wrapper")
    
    def add_document(self, document: Dict[str, Any]) -> None:
        """
        Add a document to the vector store.
        
        Args:
            document: Document data
        """
        # Run async function in sync context
        asyncio.run(self.async_store.add_document(document))
        
        # Update cache for compatibility
        self._refresh_cache()
    
    def clear(self) -> None:
        """Clear all documents from the vector store."""
        # Run async function in sync context
        asyncio.run(self.async_store.clear())
        
        # Clear cache
        self.documents = []
        self.document_embeddings = []
    
    def save(self) -> None:
        """Save the vector store (no-op in MongoDB implementation)."""
        # MongoDB saves automatically, no need to explicitly save
        logger.info("Vector store save operation (no-op in MongoDB implementation)")
    
    def get_documents(self) -> List[Dict[str, Any]]:
        """
        Get all documents in the vector store.
        
        Returns:
            List of documents
        """
        # Refresh cache if empty
        if not self.documents:
            self._refresh_cache()
        
        return self.documents
    
    def query(self, query_text: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Query the vector store for relevant documents.
        
        Args:
            query_text: Query text
            top_k: Number of top results to return
            
        Returns:
            List of relevant documents with scores
        """
        # Run async function in sync context
        return asyncio.run(self.async_store.query(query_text, top_k))
    
    def get_document_by_id(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a document by its ID.
        
        Args:
            doc_id: Document ID
            
        Returns:
            Document if found, None otherwise
        """
        # Run async function in sync context
        return asyncio.run(self.async_store.get_document_by_id(doc_id))
    
    def get_document_by_filename(self, filename: str) -> Optional[Dict[str, Any]]:
        """
        Get a document by its filename.
        
        Args:
            filename: Document filename
            
        Returns:
            Document if found, None otherwise
        """
        # Run async function in sync context
        return asyncio.run(self.async_store.get_document_by_filename(filename))
    
    def _refresh_cache(self) -> None:
        """Refresh the document cache for compatibility."""
        self.documents = asyncio.run(self.async_store.get_documents())

# Factory function to create the appropriate vector store
def create_vector_store(use_mongodb: bool = True):
    """
    Create a vector store instance.
    
    Args:
        use_mongodb: Whether to use MongoDB (True) or file-based storage (False)
        
    Returns:
        Vector store instance
    """
    if use_mongodb:
        logger.info("Creating MongoDB-based vector store")
        return VectorStoreMongoDB()
    else:
        logger.info("Creating file-based vector store")
        from app.core.vector_store import VectorStore
        return VectorStore()

# Default instance
vector_store_mongodb = None  # Will be initialized on first use

def get_vector_store():
    """Get the default vector store instance."""
    global vector_store_mongodb
    if vector_store_mongodb is None:
        vector_store_mongodb = create_vector_store(use_mongodb=True)
    return vector_store_mongodb
