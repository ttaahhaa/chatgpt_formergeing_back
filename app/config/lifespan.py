"""
FastAPI lifespan events for startup and shutdown.
"""
import logging
import traceback
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.database import initialize_database, close_database_connections
from app.core.mongodb_logger import MongoDBLogHandler, test_mongodb_logger
from app.database.repositories.factory import repository_factory

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for FastAPI application.
    Handles startup and shutdown events.
    """
    # Startup
    try:
        logger.info("Initializing database connection")
        initialized = await initialize_database()
        if not initialized:
            logger.error("Failed to initialize database")
        else:
            logger.info("Database initialized successfully")
            
            # Setup MongoDB log handler AFTER database is initialized
            try:
                # Get log repository
                log_repo = repository_factory.log_repository
                
                # Remove any existing MongoDB handlers to avoid duplicates
                root_logger = logging.getLogger()
                for handler in root_logger.handlers[:]:
                    if isinstance(handler, MongoDBLogHandler):
                        logger.info("Removing existing MongoDB log handler")
                        root_logger.removeHandler(handler)
                
                # Create and configure a new MongoDB log handler
                mongo_handler = MongoDBLogHandler(level=logging.WARNING)
                mongo_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
                
                # Initialize repository directly
                mongo_handler.repository = log_repo
                mongo_handler.ready = True
                
                # Add to root logger
                root_logger.addHandler(mongo_handler)
                
                # Log test messages
                logger.warning("MongoDB logging test - WARNING level message")
                logger.error("MongoDB logging test - ERROR level message")
                logger.info("MongoDB logger initialization complete")
                
                # Run direct test for MongoDB logging
                logger.info("Running direct MongoDB logger test")
                test_result = test_mongodb_logger()
                if test_result:
                    logger.info("Direct MongoDB logger test successful")
                else:
                    logger.error("Direct MongoDB logger test failed")
                    
            except (ValueError, AttributeError) as e:
                logger.error("Error setting up MongoDB logger: %s", str(e))
                logger.error(traceback.format_exc())
    except (ConnectionError, RuntimeError) as e:
        logger.error("Error during startup: %s", str(e))
        logger.error(traceback.format_exc())

    yield  # This is where FastAPI runs and serves requests
    
    # Shutdown
    try:
        logger.info("Closing database connections")
        await close_database_connections()
        logger.info("Database connections closed")
    except (ConnectionError, RuntimeError) as e:
        logger.error("Error during shutdown: %s", str(e))
        logger.error(traceback.format_exc())