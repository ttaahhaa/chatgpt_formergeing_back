"""
Caching utilities for Document QA Assistant.
Provides functions for caching and retrieving processed documents.
"""

import os
import pickle
import hashlib
import logging
from pathlib import Path
from typing import Any, Optional, List

from app.config import config

logger = logging.getLogger(__name__)

def get_document_hash(content: bytes) -> str:
    """
    Generate a unique hash for document content.
    
    Args:
        content: Document content as bytes
        
    Returns:
        MD5 hash of the content
    """
    return hashlib.md5(content).hexdigest()

def save_to_cache(file_hash: str, data: Any) -> bool:
    """
    Save data to cache.
    
    Args:
        file_hash: Hash key for the data
        data: Data to cache
        
    Returns:
        True if successful, False otherwise
    """
    try:
        cache_path = Path(config.cache_dir) / f"{file_hash}.pkl"
        with open(cache_path, 'wb') as f:
            pickle.dump(data, f)
        logger.info(f"Saved data to cache with hash {file_hash}")
        return True
    except Exception as e:
        logger.error(f"Error saving to cache: {str(e)}")
        return False

def load_from_cache(file_hash: str) -> Optional[Any]:
    """
    Load data from cache.
    
    Args:
        file_hash: Hash key for the data
        
    Returns:
        Cached data if found, None otherwise
    """
    try:
        cache_path = Path(config.cache_dir) / f"{file_hash}.pkl"
        if cache_path.exists():
            with open(cache_path, 'rb') as f:
                data = pickle.load(f)
            logger.info(f"Loaded data from cache with hash {file_hash}")
            return data
    except Exception as e:
        logger.error(f"Error loading from cache: {str(e)}")
    return None

def clear_cache() -> bool:
    """
    Clear all cached data.
    
    Returns:
        True if successful, False otherwise
    """
    try:
        cache_dir = Path(config.cache_dir)
        file_count = 0
        
        # Delete all pickle files in the cache directory
        for file_path in cache_dir.glob("*.pkl"):
            file_path.unlink()
            file_count += 1
        
        logger.info(f"Cleared {file_count} files from cache")
        return True
    except Exception as e:
        logger.error(f"Error clearing cache: {str(e)}")
        return False

def get_cache_info() -> dict:
    """
    Get information about the cache.
    
    Returns:
        Dictionary with cache statistics
    """
    cache_dir = Path(config.cache_dir)
    file_count = len(list(cache_dir.glob("*.pkl")))
    
    # Calculate total size
    total_size = 0
    for file_path in cache_dir.glob("*.pkl"):
        total_size += file_path.stat().st_size
    
    # Convert to MB
    size_mb = total_size / (1024 * 1024)
    
    return {
        "file_count": file_count,
        "size_mb": round(size_mb, 2),
        "cache_dir": str(cache_dir)
    }
