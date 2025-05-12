"""
Configuration settings for the Document QA Assistant with MongoDB support.
"""
import os
from pathlib import Path
from typing import Dict, List, Optional, Union
import urllib.parse

# Base directory of the project
BASE_DIR = Path(__file__).resolve().parent.parent

# Environment variables and defaults
class Config:
    """Configuration class for the application."""
    
    # Application settings
    APP_NAME: str = os.getenv("APP_NAME", "Document QA Assistant")
    DEBUG: bool = os.getenv("DEBUG", "False").lower() in ("true", "1", "t")
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    
    # Logging settings
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = os.getenv("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    LOG_DIR: Path = BASE_DIR / "logs"
    
    # Data directory settings (for backward compatibility)
    DATA_DIR: Path = BASE_DIR / "data"
    CACHE_DIR: Path = DATA_DIR / "cache"
    CONVERSATIONS_DIR: Path = DATA_DIR / "conversations"
    
    # MongoDB settings
    MONGODB_HOST: str = os.getenv("MONGODB_HOST", "localhost")
    MONGODB_PORT: int = int(os.getenv("MONGODB_PORT", "27017"))
    MONGODB_DATABASE: str = os.getenv("MONGODB_DATABASE", "document_qa")
    MONGODB_USERNAME: str = os.getenv("MONGODB_USERNAME", "")
    MONGODB_PASSWORD: str = os.getenv("MONGODB_PASSWORD", "")
    MONGODB_AUTH_SOURCE: str = os.getenv("MONGODB_AUTH_SOURCE", "admin")
    
    # Vector store settings - using MongoDB
    VECTOR_STORE_TYPE: str = os.getenv("VECTOR_STORE_TYPE", "mongodb")
    
    # Embedding settings - using local AraberT model
    EMBEDDING_MODEL_PATH: Path = BASE_DIR / "data" / "embeddings" / "arabert"
    EMBEDDING_MODEL_PATH_STR: str = str(EMBEDDING_MODEL_PATH)
    EMBEDDING_DIMENSION: int = 768
    EMBEDDING_BATCH_SIZE: int = 16
    
    # LLM settings - using local Ollama with Mistral model
    LLM_MODEL: str = os.getenv("LLM_MODEL", "mistral:latest")
    LLM_TEMPERATURE: float = 0.1
    LLM_MAX_TOKENS: int = 1024
    
    # Document processing settings
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    MAX_DOCUMENT_SIZE_MB: int = 20
    
    # Retrieval settings
    TOP_K_RETRIEVAL: int = 5
    HYBRID_ALPHA: float = 0.5  # Weight between keyword and semantic search
    
    # API settings
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8001"))  # Different port for MongoDB version
    API_WORKERS: int = int(os.getenv("API_WORKERS", "1"))
    
    # UI settings
    UI_HOST: str = os.getenv("UI_HOST", "0.0.0.0")
    UI_PORT: int = int(os.getenv("UI_PORT", "8501"))
    
    # Ollama settings
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    
    @property
    def connection_string(self) -> str:
        """Get MongoDB connection string with proper authentication."""
        if self.username and self.password:
            # URL encode username and password
            encoded_username = urllib.parse.quote_plus(self.username)
            encoded_password = urllib.parse.quote_plus(self.password)
            return f"mongodb://{encoded_username}:{encoded_password}@{self.host}:{self.port}/{self.database_name}?authSource={self.auth_source}"
        else:
            return f"mongodb://{self.host}:{self.port}/{self.database_name}"
        
    @classmethod
    def create_directories(cls) -> None:
        """Create necessary directories if they don't exist."""
        cls.LOG_DIR.mkdir(parents=True, exist_ok=True)
        cls.CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cls.CONVERSATIONS_DIR.mkdir(parents=True, exist_ok=True)
        cls.EMBEDDING_MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)

# Create an instance of the config
config = Config()

# Create necessary directories
config.create_directories()
