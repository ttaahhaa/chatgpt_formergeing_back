"""
Database migration utility for Document QA Assistant.
Handles migration from file-based storage to MongoDB.
"""
import os
import logging
import pickle
import json
import uuid
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from pathlib import Path
import asyncio

from app.config import config
from app.database.repositories.factory import repository_factory
from app.database.config import mongodb_config

logger = logging.getLogger(__name__)

class MigrationUtility:
    """Utility for migrating data from files to MongoDB."""
    
    def __init__(self):
        """Initialize the migration utility."""
        self.document_repo = repository_factory.document_repository
        self.embedding_repo = repository_factory.embedding_repository
        self.conversation_repo = repository_factory.conversation_repository
        self.knowledge_graph_repo = repository_factory.knowledge_graph_repository
        
        # File paths
        self.documents_cache_file = os.path.join(config.CACHE_DIR, "documents.pkl")
        self.embeddings_cache_file = os.path.join(config.CACHE_DIR, "embeddings.pkl")
        self.conversations_dir = config.CONVERSATIONS_DIR
        
        logger.info("Migration utility initialized")
    
    async def migrate_documents_and_embeddings(self) -> Tuple[int, int]:
        """
        Migrate documents and embeddings from pickle files to MongoDB.
        
        Returns:
            Tuple with (documents_migrated, embeddings_migrated) counts
        """
        try:
            logger.info("Starting document and embedding migration")
            
            documents_migrated = 0
            embeddings_migrated = 0
            
            # Check if documents file exists
            if not os.path.exists(self.documents_cache_file):
                logger.warning(f"Documents cache file not found: {self.documents_cache_file}")
                return (0, 0)
            
            # Load documents from pickle file
            with open(self.documents_cache_file, "rb") as f:
                documents = pickle.load(f)
            
            logger.info(f"Loaded {len(documents)} documents from cache file")
            
            # Check if embeddings file exists
            embeddings = []
            if os.path.exists(self.embeddings_cache_file):
                with open(self.embeddings_cache_file, "rb") as f:
                    embeddings = pickle.load(f)
                logger.info(f"Loaded {len(embeddings)} embeddings from cache file")
            
            # Migrate documents to MongoDB
            for i, doc in enumerate(documents):
                # Generate a document ID if not present
                if "id" not in doc:
                    doc["id"] = f"doc_{uuid.uuid4()}"
                
                # Add timestamps if not present
                if "created_at" not in doc:
                    doc["created_at"] = datetime.utcnow()
                if "updated_at" not in doc:
                    doc["updated_at"] = datetime.utcnow()
                
                # Add the document to MongoDB
                doc_id = await self.document_repo.add_document(doc)
                
                if doc_id:
                    documents_migrated += 1
                    
                    # If we have a corresponding embedding, migrate it too
                    if i < len(embeddings):
                        embedding = embeddings[i]
                        emb_id = await self.embedding_repo.add_embedding(
                            document_id=doc_id,
                            embedding=embedding.tolist() if hasattr(embedding, "tolist") else embedding,
                            model="arabert"
                        )
                        
                        if emb_id:
                            embeddings_migrated += 1
                
                # Log progress for large migrations
                if (i + 1) % 10 == 0:
                    logger.info(f"Migrated {i + 1}/{len(documents)} documents")
            
            logger.info(f"Document and embedding migration completed. "
                        f"Migrated {documents_migrated} documents and {embeddings_migrated} embeddings")
            
            return (documents_migrated, embeddings_migrated)
        
        except Exception as e:
            logger.error(f"Error during document and embedding migration: {str(e)}")
            return (0, 0)
    
    async def migrate_conversations(self) -> int:
        """
        Migrate conversations from JSON files to MongoDB.
        
        Returns:
            Number of conversations migrated
        """
        try:
            logger.info("Starting conversation migration")
            
            conversations_migrated = 0
            conversations_dir = Path(self.conversations_dir)
            
            # Check if conversations directory exists
            if not conversations_dir.exists():
                logger.warning(f"Conversations directory not found: {conversations_dir}")
                return 0
            
            # Get all JSON files in the conversations directory
            conversation_files = list(conversations_dir.glob("*.json"))
            logger.info(f"Found {len(conversation_files)} conversation files")
            
            # Migrate each conversation file
            for i, file_path in enumerate(conversation_files):
                try:
                    # Read conversation file
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    
                    # Extract conversation ID from filename
                    conv_id = file_path.stem
                    
                    # Set up conversation data
                    messages = data.get("messages", data.get("history", []))
                    preview = data.get("preview", "Conversation")
                    last_updated = data.get("last_updated", datetime.utcnow().isoformat())
                    
                    # Convert ISO string to datetime if needed
                    if isinstance(last_updated, str):
                        try:
                            last_updated = datetime.fromisoformat(last_updated)
                        except ValueError:
                            last_updated = datetime.utcnow()
                    
                    # Create conversation object
                    conversation = {
                        "id": conv_id,
                        "messages": messages,
                        "preview": preview,
                        "last_updated": last_updated
                    }
                    
                    # Add conversation to MongoDB
                    result = await self.conversation_repo.create(conversation)
                    
                    if result:
                        conversations_migrated += 1
                
                except Exception as e:
                    logger.error(f"Error migrating conversation {file_path}: {str(e)}")
                
                # Log progress for large migrations
                if (i + 1) % 10 == 0:
                    logger.info(f"Migrated {i + 1}/{len(conversation_files)} conversations")
            
            logger.info(f"Conversation migration completed. Migrated {conversations_migrated} conversations")
            
            return conversations_migrated
        
        except Exception as e:
            logger.error(f"Error during conversation migration: {str(e)}")
            return 0
    
    async def migrate_all_data(self) -> Dict[str, int]:
        """
        Migrate all data from files to MongoDB.
        
        Returns:
            Dictionary with migration statistics
        """
        try:
            logger.info("Starting full data migration")
            
            # Migrate documents and embeddings
            docs_migrated, embs_migrated = await self.migrate_documents_and_embeddings()
            
            # Migrate conversations
            convs_migrated = await self.migrate_conversations()
            
            # Migration statistics
            stats = {
                "documents_migrated": docs_migrated,
                "embeddings_migrated": embs_migrated,
                "conversations_migrated": convs_migrated,
                "migration_timestamp": datetime.utcnow().isoformat()
            }
            
            logger.info(f"Full data migration completed: {stats}")
            
            return stats
        
        except Exception as e:
            logger.error(f"Error during full data migration: {str(e)}")
            return {
                "error": str(e),
                "documents_migrated": 0,
                "embeddings_migrated": 0,
                "conversations_migrated": 0,
                "migration_timestamp": datetime.utcnow().isoformat()
            }
    
    async def verify_migration(self) -> Dict[str, Any]:
        """
        Verify the migration by comparing counts.
        
        Returns:
            Dictionary with verification statistics
        """
        try:
            logger.info("Verifying migration")
            
            # Count documents in files
            file_docs_count = 0
            if os.path.exists(self.documents_cache_file):
                with open(self.documents_cache_file, "rb") as f:
                    documents = pickle.load(f)
                file_docs_count = len(documents)
            
            # Count embeddings in files
            file_embs_count = 0
            if os.path.exists(self.embeddings_cache_file):
                with open(self.embeddings_cache_file, "rb") as f:
                    embeddings = pickle.load(f)
                file_embs_count = len(embeddings)
            
            # Count conversations in files
            file_convs_count = 0
            conversations_dir = Path(self.conversations_dir)
            if conversations_dir.exists():
                file_convs_count = len(list(conversations_dir.glob("*.json")))
            
            # Count documents in MongoDB
            db_docs_count = await self.document_repo.count({})
            
            # Count embeddings in MongoDB
            db_embs_count = await self.embedding_repo.count({})
            
            # Count conversations in MongoDB
            db_convs_count = await self.conversation_repo.count({})
            
            # Verification results
            results = {
                "file_documents_count": file_docs_count,
                "db_documents_count": db_docs_count,
                "documents_match": file_docs_count == db_docs_count,
                
                "file_embeddings_count": file_embs_count,
                "db_embeddings_count": db_embs_count,
                "embeddings_match": file_embs_count == db_embs_count,
                
                "file_conversations_count": file_convs_count,
                "db_conversations_count": db_convs_count,
                "conversations_match": file_convs_count == db_convs_count,
                
                "verification_timestamp": datetime.utcnow().isoformat()
            }
            
            # Overall verification result
            results["all_match"] = (
                results["documents_match"] and
                results["embeddings_match"] and
                results["conversations_match"]
            )
            
            logger.info(f"Migration verification completed: {results}")
            
            return results
        
        except Exception as e:
            logger.error(f"Error during migration verification: {str(e)}")
            return {"error": str(e), "all_match": False}

# Singleton instance
migration_utility = MigrationUtility()

# Async function to run migration
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
        
        # Combine stats and verification
        results = {**stats, **verification, "success": verification.get("all_match", False)}
        
        return results
    
    except Exception as e:
        logger.error(f"Error running migration: {str(e)}")
        return {"error": str(e), "success": False}

# Command-line entry point
if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Run migration
    asyncio.run(run_migration())
