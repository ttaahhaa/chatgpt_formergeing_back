"""
MongoDB database configuration for Document QA Assistant.
"""
import os
import logging
from typing import Optional
from pymongo import MongoClient
from pymongo.database import Database
from motor.motor_asyncio import AsyncIOMotorClient
from urllib.parse import quote_plus

logger = logging.getLogger(__name__)

class MongoDBConfig:
    """MongoDB configuration and connection management."""
    
    def __init__(self):
        """Initialize MongoDB configuration."""
        # MongoDB connection settings
        self.host = os.getenv("MONGODB_HOST", "localhost")
        self.port = int(os.getenv("MONGODB_PORT", "27017"))
        self.username = os.getenv("MONGODB_USERNAME", "admin")
        self.password = os.getenv("MONGODB_PASSWORD", "P@ssw0rd")
        self.database_name = os.getenv("MONGODB_DATABASE", "document_qa")
        self.auth_source = os.getenv("MONGODB_AUTH_SOURCE", "admin")

        # Connection instances (initialized on demand)
        self._client: Optional[MongoClient] = None
        self._async_client: Optional[AsyncIOMotorClient] = None
        self._db: Optional[Database] = None
        
        # Collection names
        self.users_collection = "users"
        self.documents_collection = "documents"
        self.embeddings_collection = "embeddings"
        self.conversations_collection = "conversations"
        self.knowledge_graph_collection = "knowledge_graph"
        self.logs_collection = "logs"
        
        logger.info(f"MongoDB configuration initialized for database: {self.database_name}")
    
    @property
    def connection_string(self) -> str:
        """Get MongoDB connection string with proper authentication."""
        if self.username and self.password:
            user = quote_plus(self.username)
            pwd = quote_plus(self.password)
            return f"mongodb://{user}:{pwd}@{self.host}:{self.port}/{self.database_name}?authSource={self.auth_source}"
        else:
            return f"mongodb://{self.host}:{self.port}/{self.database_name}"
    
    def get_client(self) -> MongoClient:
        """Get or create a MongoDB client."""
        if self._client is None:
            try:
                logger.info(f"Connecting to MongoDB at {self.host}:{self.port}")
                
                # Create connection arguments
                connection_args = {
                    "host": self.host,
                    "port": self.port,
                    "serverSelectionTimeoutMS": 5000  # 5 second timeout
                }
                
                # Only add authentication if username is provided
                if self.username:
                    connection_args["username"] = self.username
                    connection_args["password"] = self.password
                    connection_args["authSource"] = self.auth_source
                
                # Create client with proper args
                self._client = MongoClient(**connection_args)
                
                # Test connection
                self._client.admin.command('ping')
                logger.info("Successfully connected to MongoDB")
            except Exception as e:
                logger.error(f"Failed to connect to MongoDB: {str(e)}")
                raise
        return self._client

    def get_async_client(self) -> AsyncIOMotorClient:
        """Get or create an async MongoDB client."""
        if self._async_client is None:
            try:
                logger.info(f"Connecting to MongoDB (async) at {self.host}:{self.port}")
                self._async_client = AsyncIOMotorClient(self.connection_string)
                logger.info("Successfully connected to MongoDB (async)")
            except Exception as e:
                logger.error(f"Failed to connect to MongoDB (async): {str(e)}")
                raise
        return self._async_client
    
    def get_database(self) -> Database:
        """Get the database instance."""
        if self._db is None:
            client = self.get_client()
            self._db = client[self.database_name]
        return self._db
    
    def close_connections(self):
        """Close all MongoDB connections."""
        if self._client:
            self._client.close()
            self._client = None
        if self._async_client:
            self._async_client.close()
            self._async_client = None
        self._db = None
        logger.info("Closed all MongoDB connections")

# Create a singleton instance
mongodb_config = MongoDBConfig()
