"""
Database module for Document QA Assistant.
Provides MongoDB integration and repository pattern implementation.
"""
import logging
from typing import Optional

from app.database.config import mongodb_config

logger = logging.getLogger(__name__)

async def initialize_database() -> bool:
    """
    Initialize the database connection and create required indexes.
    
    Returns:
        True if successful, False otherwise
    """
    try:
        logger.info("Initializing MongoDB connection")
        
        # Test database connection
        client = mongodb_config.get_client()
        db = client[mongodb_config.database_name]
        
        # Ping the database to verify connection
        db.command("ping")
        
        logger.info(f"Successfully connected to MongoDB database: {mongodb_config.database_name}")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")
        return False

async def close_database_connections():
    """Close all database connections."""
    try:
        logger.info("Closing database connections")
        mongodb_config.close_connections()
        logger.info("Database connections closed")
    except Exception as e:
        logger.error(f"Error closing database connections: {str(e)}")
