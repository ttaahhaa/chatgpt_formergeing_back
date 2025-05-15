"""
Repository factory for creating and caching repository instances.
"""
import logging
from typing import Dict, Any, Optional, Type
from motor.motor_asyncio import AsyncIOMotorClient
from app.database.config import mongodb_config
from app.database.repositories.base_repository import BaseRepository
from app.database.repositories.document_repository import DocumentRepository
from app.database.repositories.embedding_repository import EmbeddingRepository
from app.database.repositories.conversation_repository import ConversationRepository
from app.database.repositories.user_repository import UserRepository
from app.database.repositories.knowledge_graph_repository import KnowledgeGraphRepository
from app.database.repositories.log_repository import LogRepository
import urllib.parse

logger = logging.getLogger(__name__)

class RepositoryFactory:
    """Factory for creating repository instances."""
    
    def __init__(self):
        """Initialize the repository factory."""
        # URL encode username and password
        username = urllib.parse.quote_plus(mongodb_config.username)
        password = urllib.parse.quote_plus(mongodb_config.password)
        
        # MongoDB client
        self.client = AsyncIOMotorClient(
            f"mongodb://{username}:{password}@{mongodb_config.host}:{mongodb_config.port}/{mongodb_config.database_name}?authSource={mongodb_config.auth_source}"
        )
        self.db = self.client[mongodb_config.database_name]
        
        # Repository classes
        self._repository_classes: Dict[str, Type[BaseRepository]] = {
            "user": UserRepository,
            "document": DocumentRepository,
            "embedding": EmbeddingRepository,
            "conversation": ConversationRepository,
            "log": LogRepository,
            "knowledge_graph": KnowledgeGraphRepository
        }
        
        # Repository instances
        self._repositories: Dict[str, BaseRepository] = {}
        logger.info("Repository factory initialized")
    
    def get_repository(self, repo_type: str) -> BaseRepository:
        """Get a repository instance."""
        if repo_type not in self._repositories:
            if repo_type not in self._repository_classes:
                logger.error(f"Invalid repository type: {repo_type}")
                raise ValueError(f"Unknown repository type: {repo_type}")
            
            # Get the collection
            collection = self.db[repo_type + "s"]  # e.g., "users", "documents", etc.
            
            # Create repository instance with collection
            self._repositories[repo_type] = self._repository_classes[repo_type](collection)
            logger.info(f"Created {repo_type} repository")
        
        return self._repositories[repo_type]
    
    @property
    def user_repository(self) -> UserRepository:
        """Get the user repository."""
        return self.get_repository("user")
    
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
    def log_repository(self) -> LogRepository:
        """Get the log repository."""
        return self.get_repository("log")
    
    @property
    def knowledge_graph_repository(self) -> KnowledgeGraphRepository:
        """Get the knowledge graph repository."""
        return self.get_repository("knowledge_graph")
    
    async def close(self):
        """Close the MongoDB connection."""
        self.client.close()

# Create a singleton instance
repository_factory = RepositoryFactory()
