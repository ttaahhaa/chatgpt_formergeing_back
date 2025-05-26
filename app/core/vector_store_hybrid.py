# app/core/vector_store_hybrid.py
import os
import logging
import numpy as np
import uuid
from typing import List, Dict, Any, Optional, Tuple
import asyncio
import tempfile
import pickle
import faiss

from app.core.embeddings import Embeddings
from app.database.repositories.factory import repository_factory

logger = logging.getLogger(__name__)

class HybridVectorStore:
    """Class for managing vector embeddings using MongoDB storage and FAISS indexing."""
    
    def __init__(self):
        """Initialize the hybrid vector store."""
        self.embeddings_model = Embeddings()  # Use ArabERT by default
        self.document_repo = repository_factory.document_repository
        self.embedding_repo = repository_factory.embedding_repository
        
        # FAISS index and mappings
        self.faiss_index = None
        self.document_id_map = []  # Maps FAISS index positions to document IDs
        self.index_initialized = False
        
        # Cache directory for saving/loading FAISS index
        self.cache_dir = os.path.join(tempfile.gettempdir(), "faiss_cache")
        os.makedirs(self.cache_dir, exist_ok=True)
        self.faiss_cache_path = os.path.join(self.cache_dir, "faiss_index.bin")
        self.mapping_cache_path = os.path.join(self.cache_dir, "document_id_map.pkl")
        
        logger.info("Initialized hybrid MongoDB/FAISS vector store")
    
    async def initialize_faiss_index(self, force_rebuild: bool = False) -> bool:
        """
        Initialize the FAISS index from MongoDB embeddings.
        
        Args:
            force_rebuild: Force rebuild the index even if cached index exists
            
        Returns:
            True if successful, False otherwise
        """
        if self.index_initialized and not force_rebuild:
            return True
            
        try:
            # Try to load from cache first (if not forcing rebuild)
            if not force_rebuild and os.path.exists(self.faiss_cache_path) and os.path.exists(self.mapping_cache_path):
                try:
                    logger.info("Loading FAISS index from cache")
                    self.faiss_index = faiss.read_index(self.faiss_cache_path)
                    
                    with open(self.mapping_cache_path, 'rb') as f:
                        self.document_id_map = pickle.load(f)
                    
                    self.index_initialized = True
                    logger.info(f"Loaded FAISS index with {len(self.document_id_map)} vectors from cache")
                    return True
                except Exception as e:
                    logger.warning(f"Failed to load FAISS index from cache: {str(e)}")
                    # Continue to rebuild
            
            # Fetch all embeddings from MongoDB
            logger.info("Building FAISS index from MongoDB embeddings")
            embeddings = await self.embedding_repo.find({})
            
            # Create document ID mapping and vectors list
            vectors = []
            self.document_id_map = []
            
            for emb in embeddings:
                # Get the embedding vector from dictionary
                vector = emb["embedding"]
                
                # Convert to numpy array if necessary
                if not isinstance(vector, np.ndarray):
                    vector = np.array(vector, dtype=np.float32)
                
                # Add to vectors list and document ID map
                vectors.append(vector)
                self.document_id_map.append(emb["document_id"])
            
            # If we have vectors, create the FAISS index
            if vectors:
                # Convert to numpy array
                embeddings_array = np.array(vectors).astype(np.float32)
                
                # Create FAISS index (using inner product similarity, which is equivalent to cosine similarity on normalized vectors)
                dimension = embeddings_array.shape[1]
                self.faiss_index = faiss.IndexFlatIP(dimension)
                
                # Normalize vectors for cosine similarity
                faiss.normalize_L2(embeddings_array)
                
                # Add vectors to index
                self.faiss_index.add(embeddings_array)
                
                # Save to cache
                try:
                    faiss.write_index(self.faiss_index, self.faiss_cache_path)
                    with open(self.mapping_cache_path, 'wb') as f:
                        pickle.dump(self.document_id_map, f)
                    logger.info("Saved FAISS index to cache")
                except Exception as e:
                    logger.warning(f"Failed to save FAISS index to cache: {str(e)}")
            else:
                # No vectors, create empty index
                self.faiss_index = faiss.IndexFlatIP(768)  # Default dimension for ArabERT
                self.document_id_map = []
            
            self.index_initialized = True
            logger.info(f"Built FAISS index with {len(self.document_id_map)} vectors")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing FAISS index: {str(e)}")
            return False
    
    async def add_document(self, document: Dict[str, Any]) -> bool:
        """
        Add a document to the vector store.
        
        Args:
            document: Document data including content and metadata
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Adding document to MongoDB: {document}")
            # Generate a unique document ID if not present
            if "id" not in document:
                document["id"] = f"doc_{uuid.uuid4()}"
            
            document_id = document["id"]
            
            # Check if document already exists by filename
            existing = await self.document_repo.find_by_filename(document.get("filename", ""))
            if existing:
                logger.info(f"Document already exists: {document.get('filename', '')}")
                document_id = existing.id
                # We'll update the embedding below
            else:
                # Add document to MongoDB with our generated ID
                doc_id = await self.document_repo.create(document)
                if not doc_id:
                    logger.error("Failed to add document to MongoDB")
                    return False
                # Use our generated ID instead of MongoDB's
                document_id = document["id"]
            
            # Generate embedding for document content
            content = document.get("content", "")
            if not content or content.startswith("[Error") or content.startswith("[No readable content"):
                logger.warning(f"Skipping embedding generation for document with error: {content}")
                return True
            
            try:
                embedding = self.embeddings_model.get_embeddings(content)
                
                # Add embedding to MongoDB with our document ID
                emb_id = await self.embedding_repo.add_embedding(
                    document_id=document_id,  # Use our generated ID
                    embedding=embedding[0].tolist() if hasattr(embedding[0], "tolist") else embedding[0],
                    model="arabert"
                )
                
                if not emb_id:
                    logger.warning(f"Failed to add embedding for document {document_id}")
                    return False
                
                # Force rebuild FAISS index to ensure consistency
                success = await self.initialize_faiss_index(force_rebuild=True)
                if not success:
                    logger.error("Failed to rebuild FAISS index after adding document")
                    return False
                
                logger.info(f"Added document: {document.get('filename', 'unknown')}")
                return True
                
            except Exception as e:
                logger.error(f"Error generating embedding: {str(e)}")
                # If embedding fails, we should clean up the document
                await self.document_repo.delete(document_id)
                return False
                
        except Exception as e:
            logger.error(f"Error adding document to MongoDB: {str(e)}")
            return False
    
    async def _update_faiss_index(self) -> bool:
        """
        Update the FAISS index after adding or removing documents.
        
        Returns:
            True if successful, False otherwise
        """
        # For simplicity, we'll rebuild the entire index
        # In a production system, you might want to use a more incremental approach
        return await self.initialize_faiss_index(force_rebuild=True)
    
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
                # Get document ID safely
                doc_id = doc.get("id") if isinstance(doc, dict) else doc.id
                
                # Delete embedding first (to maintain referential integrity)
                emb_deleted = await self.embedding_repo.delete_by_document_id(doc_id)
                
                # Delete document
                doc_deleted = await self.document_repo.delete(doc_id)
                
                if not doc_deleted:
                    logger.warning(f"Failed to delete document {doc_id}")
                    success = False
            
            # Reset FAISS index
            self.faiss_index = faiss.IndexFlatIP(768)  # Default dimension for ArabERT
            self.document_id_map = []
            self.index_initialized = False  # Force reinitialization on next use
            
            # Try to delete cache files
            try:
                if os.path.exists(self.faiss_cache_path):
                    os.remove(self.faiss_cache_path)
                if os.path.exists(self.mapping_cache_path):
                    os.remove(self.mapping_cache_path)
            except Exception as e:
                logger.warning(f"Failed to delete cache files: {str(e)}")
            
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
        Query the vector store for relevant documents using FAISS.
        
        Args:
            query_text: Query text
            top_k: Number of top results to return
            
        Returns:
            List of relevant documents with scores
        """
        try:
            if not query_text:
                logger.warning("Empty query text provided")
                return []
            
            # Log FAISS index status
            logger.info(f"FAISS index initialized: {self.index_initialized}")
            if self.faiss_index:
                logger.info(f"FAISS index total vectors: {self.faiss_index.ntotal}")
                logger.info(f"FAISS index dimension: {self.faiss_index.d}")
            else:
                logger.warning("FAISS index is None")
            
            # Ensure FAISS index is initialized
            if not self.index_initialized:
                logger.info("Initializing FAISS index...")
                await self.initialize_faiss_index()
                logger.info(f"FAISS index initialization complete. Total vectors: {self.faiss_index.ntotal if self.faiss_index else 0}")
            
            # If index is empty or failed to initialize
            if self.faiss_index is None or self.faiss_index.ntotal == 0:
                logger.warning("FAISS index is empty or not initialized")
                return []
            
            # Generate embedding for the query
            logger.info("Generating query embedding...")
            query_embedding = self.embeddings_model.get_embeddings(query_text)[0]
            query_np = np.array([query_embedding]).astype(np.float32)
            logger.info(f"Query embedding shape: {query_np.shape}")
            
            # Normalize query vector for cosine similarity
            faiss.normalize_L2(query_np)
            
            # Search in FAISS index
            logger.info(f"Searching FAISS index with top_k={top_k}")
            scores, indices = self.faiss_index.search(query_np, min(top_k, self.faiss_index.ntotal))
            logger.info(f"FAISS search results - scores: {scores}, indices: {indices}")
            
            # Flatten results
            scores = scores[0]
            indices = indices[0]
            
            # Get document IDs from mapping
            results = []
            logger.info(f"Document ID map size: {len(self.document_id_map)}")
            
            for i, idx in enumerate(indices):
                if idx < 0 or idx >= len(self.document_id_map):
                    logger.warning(f"Invalid index {idx} in FAISS results")
                    continue
                
                # Get document ID
                doc_id = self.document_id_map[idx]
                logger.info(f"Processing document ID: {doc_id}")
                
                # Get document from MongoDB
                document = await self.document_repo.find_by_id(doc_id)
                if document:
                    logger.info(f"Found document in MongoDB: {doc_id}")
                    # Document is already a dictionary, just add the score
                    doc_dict = document.copy()
                    doc_dict["score"] = float(scores[i])
                    results.append(doc_dict)
                else:
                    logger.warning(f"Document not found in MongoDB: {doc_id}")
            
            logger.info(f"Query: '{query_text}' returned {len(results)} results")
            if results:
                logger.info(f"Top result score: {results[0]['score']}")
            return results
            
        except Exception as e:
            logger.error(f"Error querying vector store: {str(e)}", exc_info=True)
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

class SyncHybridVectorStore:
    """
    Synchronous wrapper around the async HybridVectorStore.
    Maintains compatibility with the existing API.
    """
    
    def __init__(self):
        """Initialize the sync vector store."""
        self.async_store = HybridVectorStore()
        self.documents = []  # Cache for compatibility
        self.document_embeddings = []  # Cache for compatibility
        self.index_initialized = False
        logger.info("Initialized synchronous Hybrid vector store wrapper")
        
        # Don't initialize FAISS index in constructor
        # We'll do it lazily when needed
    
    def _ensure_index_initialized(self):
        """Ensure the FAISS index is initialized."""
        if not self.index_initialized:
            # Try to get the current event loop
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                # If no event loop exists in this thread, create a new one
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            # Run the initialization
            if loop.is_running():
                # If we're already in an event loop (e.g., inside FastAPI)
                # Create a future and run it in the background
                future = asyncio.run_coroutine_threadsafe(
                    self.async_store.initialize_faiss_index(),
                    loop
                )
                # Wait for the result with a timeout
                future.result(timeout=30)
            else:
                # If no event loop is running, we can use run_until_complete
                loop.run_until_complete(self.async_store.initialize_faiss_index())
            
            self.index_initialized = True
    
    def add_document(self, document: Dict[str, Any]) -> None:
        """
        Add a document to the vector store.
        
        Args:
            document: Document data
        """
        # Ensure the index is initialized
        self._ensure_index_initialized()
        
        # Try to get the current event loop
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            # If no event loop exists in this thread, create a new one
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # Run the async function
        if loop.is_running():
            # If we're already in an event loop
            future = asyncio.run_coroutine_threadsafe(
                self.async_store.add_document(document),
                loop
            )
            future.result(timeout=30)
        else:
            # If no event loop is running
            loop.run_until_complete(self.async_store.add_document(document))
        
        # Update cache for compatibility
        self._refresh_cache()
    
    def clear(self) -> None:
        """Clear all documents from the vector store."""
        # Try to get the current event loop
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            # If no event loop exists in this thread, create a new one
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # Run the async function
        if loop.is_running():
            # If we're already in an event loop
            future = asyncio.run_coroutine_threadsafe(
                self.async_store.clear(),
                loop
            )
            future.result(timeout=30)
        else:
            # If no event loop is running
            loop.run_until_complete(self.async_store.clear())
        
        # Clear cache
        self.documents = []
        self.document_embeddings = []
        self.index_initialized = False
    
    def save(self) -> None:
        """Save the vector store (in this implementation, rebuilds FAISS index)."""
        # Ensure the index is initialized
        self._ensure_index_initialized()
        
        # Try to get the current event loop
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            # If no event loop exists in this thread, create a new one
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # Run the async function
        if loop.is_running():
            # If we're already in an event loop
            future = asyncio.run_coroutine_threadsafe(
                self.async_store._update_faiss_index(),
                loop
            )
            future.result(timeout=30)
        else:
            # If no event loop is running
            loop.run_until_complete(self.async_store._update_faiss_index())
        
        logger.info("Vector store saved (FAISS index rebuilt)")
    
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
        # Ensure the index is initialized
        self._ensure_index_initialized()
        
        # Try to get the current event loop
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            # If no event loop exists in this thread, create a new one
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # Run the async function
        if loop.is_running():
            # If we're already in an event loop
            future = asyncio.run_coroutine_threadsafe(
                self.async_store.query(query_text, top_k),
                loop
            )
            return future.result(timeout=30)
        else:
            # If no event loop is running
            return loop.run_until_complete(self.async_store.query(query_text, top_k))
    
    def get_document_by_id(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a document by its ID.
        
        Args:
            doc_id: Document ID
            
        Returns:
            Document if found, None otherwise
        """
        # Try to get the current event loop
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            # If no event loop exists in this thread, create a new one
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # Run the async function
        if loop.is_running():
            # If we're already in an event loop
            future = asyncio.run_coroutine_threadsafe(
                self.async_store.get_document_by_id(doc_id),
                loop
            )
            return future.result(timeout=30)
        else:
            # If no event loop is running
            return loop.run_until_complete(self.async_store.get_document_by_id(doc_id))
    
    def get_document_by_filename(self, filename: str) -> Optional[Dict[str, Any]]:
        """
        Get a document by its filename.
        
        Args:
            filename: Document filename
            
        Returns:
            Document if found, None otherwise
        """
        # Try to get the current event loop
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            # If no event loop exists in this thread, create a new one
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # Run the async function
        if loop.is_running():
            # If we're already in an event loop
            future = asyncio.run_coroutine_threadsafe(
                self.async_store.get_document_by_filename(filename),
                loop
            )
            return future.result(timeout=30)
        else:
            # If no event loop is running
            return loop.run_until_complete(self.async_store.get_document_by_filename(filename))
    
    def _refresh_cache(self) -> None:
        """Refresh the document cache for compatibility."""
        # Try to get the current event loop
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            # If no event loop exists in this thread, create a new one
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # Run the async function
        if loop.is_running():
            # If we're already in an event loop
            future = asyncio.run_coroutine_threadsafe(
                self.async_store.get_documents(),
                loop
            )
            self.documents = future.result(timeout=30)
        else:
            # If no event loop is running
            self.documents = loop.run_until_complete(self.async_store.get_documents())
            
# Factory function
def create_hybrid_vector_store():
    """Create a hybrid vector store instance."""
    logger.info("Creating hybrid MongoDB/FAISS vector store")
    return SyncHybridVectorStore()

# Default instance
hybrid_vector_store = None

def get_hybrid_vector_store():
    """Get the default hybrid vector store instance."""
    global hybrid_vector_store
    if hybrid_vector_store is None:
        hybrid_vector_store = create_hybrid_vector_store()
    return hybrid_vector_store