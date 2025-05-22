"""
Application configuration and component initialization.
Centralizes all the initialization logic that was in main.py.

This module serves as the central hub for managing all application components.
It implements a lazy loading pattern to avoid circular imports and improve startup performance.
Components are only initialized when they are first accessed.

Key features:
- Centralized logging configuration
- Lazy loading of all application components
- Component access through properties
- Global components instance for application-wide access
"""
import logging
import os
from datetime import datetime
from app.utils.logging_utils import setup_logging

# Setup logging first
today = datetime.now().strftime("%Y%m%d")
base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
logs_dir = os.path.join(base_dir, "logs")
os.makedirs(logs_dir, exist_ok=True)
log_file = os.path.join(logs_dir, f"app_mongodb_{today}.log")

class AppComponents:
    """
    Container for all application components using lazy loading.
    
    This class manages the lifecycle of all application components and provides
    access to them through properties. Components are initialized only when first
    accessed, which helps avoid circular imports and improves startup performance.
    
    Available components:
    - document_loader: Handles document loading and processing
    - vector_store: Manages vector storage for embeddings
    - llm_chain: Main language model chain for processing
    - retriever: Hybrid retrieval system
    - streaming_llm: Streaming version of the language model
    - document_repo: Document database repository
    - embedding_repo: Embedding database repository
    - conversation_repo: Conversation database repository
    - user_repo: User database repository
    """
    
    def __init__(self):
        """
        Initialize logging only, defer component loading.
        
        Sets up logging configuration and initializes component placeholders.
        Actual component initialization is deferred until first access.
        """
        self.logger = setup_logging(log_file=log_file, log_level="INFO", app_name="app_mongodb")
        self.logger.info("MongoDB API Service starting")
        
        # Use lazy loading to avoid circular imports
        self._document_loader = None
        self._vector_store = None
        self._llm_chain = None
        self._retriever = None
        self._streaming_llm = None
        self._document_repo = None
        self._embedding_repo = None
        self._conversation_repo = None
        self._user_repo = None

    @property
    def document_loader(self):
        if self._document_loader is None:
            from app.core.document_loader import DocumentLoader
            self._document_loader = DocumentLoader()
        return self._document_loader

    @property
    def vector_store(self):
        if self._vector_store is None:
            from app.core.vector_store_hybrid import get_hybrid_vector_store
            self._vector_store = get_hybrid_vector_store()
        return self._vector_store

    @property
    def llm_chain(self):
        if self._llm_chain is None:
            from app.core.llm import LLMChain
            self._llm_chain = LLMChain()
        return self._llm_chain

    @property
    def retriever(self):
        if self._retriever is None:
            from app.core.hybrid_retrieval import HybridRetriever
            self._retriever = HybridRetriever()
        return self._retriever

    @property
    def streaming_llm(self):
        if self._streaming_llm is None:
            from app.core.llm_streaming import StreamingLLMChain
            self._streaming_llm = StreamingLLMChain()
        return self._streaming_llm

    @property
    def document_repo(self):
        if self._document_repo is None:
            from app.database.repositories.factory import repository_factory
            self._document_repo = repository_factory.document_repository
        return self._document_repo

    @property
    def embedding_repo(self):
        if self._embedding_repo is None:
            from app.database.repositories.factory import repository_factory
            self._embedding_repo = repository_factory.embedding_repository
        return self._embedding_repo

    @property
    def conversation_repo(self):
        if self._conversation_repo is None:
            from app.database.repositories.factory import repository_factory
            self._conversation_repo = repository_factory.conversation_repository
        return self._conversation_repo

    @property
    def user_repo(self):
        if self._user_repo is None:
            from app.database.repositories.factory import repository_factory
            self._user_repo = repository_factory.user_repository
        return self._user_repo

# Global components instance for application-wide access
components = AppComponents()