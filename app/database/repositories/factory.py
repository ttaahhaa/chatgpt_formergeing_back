"""
Repository factory for creating and caching repository instances.
"""
import logging
from typing import Dict, Any, Optional, Type

from app.database.repositories.base_repository import BaseRepository
from app.database.repositories.document_repository import DocumentRepository
from app.database.repositories.embedding_repository import EmbeddingRepository
from app.database.repositories.conversation_repository import ConversationRepository
from app.database.repositories.user_repository import UserRepository
from app.database.repositories.knowledge_graph_repository import KnowledgeGraphRepository

logger = logging.getLogger(__name__)

class RepositoryFactory:
    """Factory for creating repository instances."""
    
    def __init__(self):
        """Initialize the repository factory."""
        self._repositories = {}
        self._repository_classes = {
            "document": DocumentRepository,
            "embedding": EmbeddingRepository,
            "conversation": ConversationRepository,
            "user": UserRepository,
            "knowledge_graph": KnowledgeGraphRepository
        }
        logger.info("Repository factory initialized")
    
    def get_repository(self, repo_type: str) -> Any:
        """
        Get a repository instance by type.
        
        Args:
            repo_type: Repository type
            
        Returns:
            Repository instance
        """
        if repo_type not in self._repositories:
            if repo_type not in self._repository_classes:
                logger.error(f"Invalid repository type: {repo_type}")
                raise ValueError(f"Invalid repository type: {repo_type}")
            
            # Create new repository instance
            self._repositories[repo_type] = self._repository_classes[repo_type]()
            logger.info(f"Created {repo_type} repository")
        
        return self._repositories[repo_type]
    
    @property
    def document_repository(self) -> DocumentRepository:
        """Get the document repository."""
        return self.get_repository("document")
    
    @property
    def embedding_repository(self) -> EmbeddingRepository:
        """Get the embedding repository."""
        return self.get_repository("embedding")
    
    @property
    def conversation_repository(self) -> ConversationRepository:
        """Get the conversation repository."""
        return self.get_repository("conversation")
    
    @property
    def user_repository(self) -> UserRepository:
        """Get the user repository."""
        return self.get_repository("user")
    
    @property
    def knowledge_graph_repository(self) -> KnowledgeGraphRepository:
        """Get the knowledge graph repository."""
        return self.get_repository("knowledge_graph")

# Create a singleton instance
repository_factory = RepositoryFactory()
