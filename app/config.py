"""
Configuration settings for the Document QA Assistant.
"""
import os
from pathlib import Path
from typing import Dict, List, Optional, Union

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
    
    # Data directory settings
    DATA_DIR: Path = BASE_DIR / "data"
    CACHE_DIR: Path = DATA_DIR / "cache"
    CONVERSATIONS_DIR: Path = DATA_DIR / "conversations"
    
    # Vector store settings
    VECTOR_STORE_TYPE: str = os.getenv("VECTOR_STORE_TYPE", "faiss")
    VECTOR_STORE_PATH: Path = CACHE_DIR / "vector_store"
    
    # Embedding settings - using local AraberT model with relative path
    # Using a path relative to the project root directory
    EMBEDDING_MODEL_PATH: Path = BASE_DIR / "data" / "embeddings" / "arabert"
    # Convert to string representation for compatibility
    EMBEDDING_MODEL_PATH_STR: str = str(EMBEDDING_MODEL_PATH)
    EMBEDDING_DIMENSION: int = 768  # Will be updated based on actual model dimension when loaded
    EMBEDDING_BATCH_SIZE: int = 16  # Smaller batch size for AraberT to avoid OOM
    
    # LLM settings - using local Ollama with Mistral model
    LLM_MODEL: str = "mistral:latest"
    LLM_TEMPERATURE: float = 0.1
    LLM_MAX_TOKENS: int = 1024
    
    # Document processing settings
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    MAX_DOCUMENT_SIZE_MB: int = 20
    
    # Retrieval settings
    TOP_K_RETRIEVAL: int = 5
    HYBRID_ALPHA: float = 0.5  # Weight between keyword and semantic search
    
    # Cache settings
    CACHE_ENABLED: bool = True
    CACHE_TTL: int = 3600  # seconds
    
    # API settings
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    API_WORKERS: int = int(os.getenv("API_WORKERS", "1"))
    
    # UI settings
    UI_HOST: str = os.getenv("UI_HOST", "0.0.0.0")
    UI_PORT: int = int(os.getenv("UI_PORT", "8501"))
    
    # Ollama settings
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    
    @classmethod
    def create_directories(cls) -> None:
        """Create necessary directories if they don't exist."""
        cls.LOG_DIR.mkdir(parents=True, exist_ok=True)
        cls.CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cls.CONVERSATIONS_DIR.mkdir(parents=True, exist_ok=True)
        cls.VECTOR_STORE_PATH.parent.mkdir(parents=True, exist_ok=True)


# Create an instance of the config
config = Config()

# Create necessary directories
config.create_directories()
