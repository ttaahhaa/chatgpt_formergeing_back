#!/usr/bin/env python
"""
MongoDB Migration Script for Document QA Assistant.
Run this script to migrate from file-based storage to MongoDB.
"""
import os
import sys
import asyncio
import logging
import argparse
from datetime import datetime

from app.database import migration_utility

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f"migration_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    ]
)
logger = logging.getLogger("migration")

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def run_migration():
    """Run the migration process."""
    try:
        logger.info("Starting migration process")
        
        # Import MongoDB modules
        from app.database import initialize_database
        from app.database.migration_utility import migration_utility
        
        # Initialize database
        logger.info("Initializing database connection")
        initialized = await initialize_database()
        
        if not initialized:
            logger.error("Failed to initialize database. Migration aborted.")
            return 1
        
        logger.info("Database connection initialized successfully")
        
        # Run migration
        logger.info("Running full data migration")
        stats = await migration_utility.migrate_all_data()
        
        # Log statistics
        logger.info(f"Migration completed with the following statistics:")
        logger.info(f"Documents migrated: {stats.get('documents_migrated', 0)}")
        logger.info(f"Embeddings migrated: {stats.get('embeddings_migrated', 0)}")
        logger.info(f"Conversations migrated: {stats.get('conversations_migrated', 0)}")
        
        # Verify migration
        logger.info("Verifying migration")
        verification = await migration_utility.verify_migration()
        
        if verification.get("all_match", False):
            logger.info("Migration verification successful. All data migrated correctly.")
        else:
            logger.warning("Migration verification found discrepancies:")
            logger.warning(f"File documents: {verification.get('file_documents_count', 0)}, DB documents: {verification.get('db_documents_count', 0)}")
            logger.warning(f"File embeddings: {verification.get('file_embeddings_count', 0)}, DB embeddings: {verification.get('db_embeddings_count', 0)}")
            logger.warning(f"File conversations: {verification.get('file_conversations_count', 0)}, DB conversations: {verification.get('db_conversations_count', 0)}")
        
        # Close connections
        from app.database import close_database_connections
        await close_database_connections()
        
        return 0
    except Exception as e:
        logger.error(f"Error during migration: {str(e)}", exc_info=True)
        return 1

async def run_migration():
    """Run the full migration process."""
    try:
        # Initialize database
        from app.database import initialize_database
        db_initialized = await initialize_database()
        
        if not db_initialized:
            logger.error("Database initialization failed. Migration aborted.")
            return {"error": "Database initialization failed", "success": False}
        
        # Run migration
        stats = await migration_utility.migrate_all_data()
        
        # Verify migration
        verification = await migration_utility.verify_migration()
        
        # Build FAISS index after migration
        from app.core.vector_store_hybrid import HybridVectorStore
        hybrid_store = HybridVectorStore()
        faiss_success = await hybrid_store.initialize_faiss_index(force_rebuild=True)
        
        # Combine stats and verification
        results = {
            **stats, 
            **verification, 
            "success": verification.get("all_match", False),
            "faiss_index_built": faiss_success
        }
        
        return results
    
    except Exception as e:
        logger.error(f"Error running migration: {str(e)}")
        return {"error": str(e), "success": False}
    
def main():
    """Script entry point."""
    parser = argparse.ArgumentParser(description="Migrate data from file-based storage to MongoDB")
    parser.add_argument("--verify-only", action="store_true", help="Only verify migration without migrating data")
    parser.add_argument("--mongodb-host", help="MongoDB host (default: localhost)")
    parser.add_argument("--mongodb-port", type=int, help="MongoDB port (default: 27017)")
    parser.add_argument("--mongodb-db", help="MongoDB database name (default: document_qa)")
    parser.add_argument("--mongodb-user", help="MongoDB username")
    parser.add_argument("--mongodb-password", help="MongoDB password")
    
    args = parser.parse_args()
    
    # Set environment variables if provided
    if args.mongodb_host:
        os.environ["MONGODB_HOST"] = args.mongodb_host
    if args.mongodb_port:
        os.environ["MONGODB_PORT"] = str(args.mongodb_port)
    if args.mongodb_db:
        os.environ["MONGODB_DATABASE"] = args.mongodb_db
    if args.mongodb_user:
        os.environ["MONGODB_USERNAME"] = args.mongodb_user
    if args.mongodb_password:
        os.environ["MONGODB_PASSWORD"] = args.mongodb_password
    
    if args.verify_only:
        async def verify_only():
            try:
                from app.database import initialize_database
                from app.database.migration_utility import migration_utility
                
                initialized = await initialize_database()
                if not initialized:
                    logger.error("Failed to initialize database")
                    return 1
                
                verification = await migration_utility.verify_migration()
                logger.info(f"Verification results: {verification}")
                
                from app.database import close_database_connections
                await close_database_connections()
                
                return 0 if verification.get("all_match", False) else 1
            except Exception as e:
                logger.error(f"Error during verification: {str(e)}", exc_info=True)
                return 1
        
        return asyncio.run(verify_only())
    else:
        return asyncio.run(run_migration())

if __name__ == "__main__":
    sys.exit(main())
